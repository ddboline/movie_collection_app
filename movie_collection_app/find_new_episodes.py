#!/usr/bin/python
from __future__ import (absolute_import, division, print_function, unicode_literals)
import argparse
import datetime
import time
import os
import re
from dateutil.parser import parse
from collections import defaultdict
from sqlalchemy import create_engine
import pandas as pd

from movie_collection_app.trakt_instance import TraktInstance
from movie_collection_app.movie_collection import MovieCollection
from movie_collection_app.parse_imdb import (parse_imdb_episode_list, parse_imdb_tv_listings,
                                             parse_imdb_main)
from movie_collection_app.util import POSTGRESTRING

list_of_commands = ('list', 'search', 'wl', 'tv')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)
watchlist = {
    '12_monkeys', 'adventure_time', 'archer', 'homeland', 'game_of_thrones', 'lost_girl',
    'mr_robot', 'rick_and_morty', 'vikings', 'last_week_tonight_with_john_oliver',
    'outlander_2014', 'silicon_valley', 'the_last_panthers', 'the_night_manager',
    'fear_the_walking_dead', 'unreal'
}

pg_db = '%s:5432/movie_queue' % POSTGRESTRING
engine = create_engine(pg_db)


def find_upcoming_episodes(df=None, do_update=False):
    cache_file = '/tmp/parse_imdb_tv_listings.csv.gz'
    if os.path.exists(cache_file) and os.stat(cache_file).st_mtime > time.time() - 86400:
        df = pd.read_csv(cache_file, compression='gzip')

    if df is None:
        df = parse_imdb_tv_listings()
        df.to_csv(cache_file, compression='gzip', encoding='utf-8')

    with engine.connect() as db:
        query = """
            SELECT
                t1.show,
                t1.season,
                t1.episode,
                t2.title,
                t2.link as imdb_url,
                t1.epurl as ep_url
            FROM imdb_episodes t1
            JOIN imdb_ratings t2 ON t1.show = t2.show
        """
        rating_df = pd.read_sql(query, db)
    imdb_urls = set(rating_df.imdb_url.unique())
    ep_urls = set(rating_df.ep_url.unique())

    def clean_string(x):
        try:
            x = x.encode(errors='ignore').lower().split('(')[0].strip().replace(' ', '_')
        except:
            x = x.decode(errors='ignore').lower().split('(')[0].strip().replace(' ', '_')
        return x.replace("'", '').replace('&', 'and').replace(':', '')

    titles = set(map(clean_string, rating_df.title.unique()))

    df.title = df.title.apply(clean_string)

    cond0 = df.imdb_url.isin(imdb_urls)
    cond0 &= -df.ep_url.isin(ep_urls)
    cond1 = -df.imdb_url.isin(imdb_urls)
    cond1 &= df.title.isin(titles)
    df = df[cond0 | cond1].reset_index(drop=True)

    mq_ = MovieCollection()
    ti_ = TraktInstance()

    trakt_watchlist_shows = ti_.get_watchlist_shows()
    trakt_watched_shows = ti_.get_watched_shows()

    max_season = {}
    current_shows = set()
    imdb_show_map = {v['link']: k for k, v in mq_.imdb_ratings.items()}

    for row in mq_.current_queue:
        show = row['show']
        fname = row['path']
        season, episode = mq_.get_season_episode_from_name(fname, show)
        if season == -1 or episode == -1:
            continue
        imdb_url = mq_.imdb_ratings[show]['link']
        max_s = max_season.get(imdb_url, -1)
        current_shows.add(imdb_url)
        max_season[imdb_url] = max(max_s, season)

    for imdb_url, showinfo in trakt_watchlist_shows.items():
        if imdb_url in current_shows:
            continue
        current_shows.add(imdb_url)
        show = imdb_show_map.get(imdb_url, showinfo.title.lower().replace(' ', '_'))
        if imdb_url not in imdb_show_map:
            imdb_show_map[imdb_url] = show
        max_season[imdb_url] = -1

    for imdb_url in current_shows:
        if imdb_url in trakt_watched_shows:
            for s, e in sorted(trakt_watched_shows[imdb_url]):
                max_s = max_season.get(imdb_url, -1)
                max_season[imdb_url] = max(s, max_s)

    imdb_urls = set(df.imdb_url.dropna().unique())
    titles = set(df.title.unique())

    for imdb_url in sorted(current_shows):
        show = imdb_show_map[imdb_url]
        max_s = max_season[imdb_url]
        if imdb_url not in imdb_urls and show not in titles and not any(x in show for x in titles):
            continue
        print(show, imdb_url, max_s)

        season_episode_ratings = defaultdict(dict)
        for (s, e), v in mq_.imdb_episode_ratings[show].items():
            season_episode_ratings[s][e] = float(v['rating'])
        if not imdb_url:
            continue

        for item in parse_imdb_episode_list(imdb_url, season=-1):
            season = item[0]
            nepisodes = item[3]
            if season < max_s:
                continue
            if nepisodes == len([k for k, v in season_episode_ratings[season].items() if v > 0]):
                continue
            parse_imdb_main(show, do_tv=True, do_update=do_update, season=season)

    return df


def find_new_episodes(search=(), do_update=False):
    output = {}
    mq_ = MovieCollection()
    ti_ = TraktInstance()

    trakt_watchlist_shows = ti_.get_watchlist_shows()
    trakt_watched_shows = ti_.get_watched_shows()

    current_shows = set()
    max_season = {}
    max_episode = defaultdict(dict)
    current_seasons = defaultdict(set)
    current_episodes = defaultdict(set)
    maxdate = datetime.date.today()
    imdb_show_map = {v['link']: k for k, v in mq_.imdb_ratings.items()}

    try:
        if len(search) > 0:
            maxdate = parse(search[0]).date()
            search = ()
    except (TypeError, ValueError):
        pass

    for row in mq_.current_queue:
        show = row['show']
        if search and any(x not in show for x in search):
            continue
        fname = row['path']
        season, episode = mq_.get_season_episode_from_name(fname, show)
        if season == -1 or episode == -1:
            continue
        imdb_url = mq_.imdb_ratings[show]['link']
        max_s = max_season.get(imdb_url, -1)
        max_e = max_episode.get(imdb_url, {}).get(season, -1)
        current_shows.add(imdb_url)
        max_season[imdb_url] = max(max_s, season)
        max_episode[imdb_url][season] = max(max_e, episode)
        current_seasons[imdb_url].add(season)
        current_episodes[imdb_url].add((season, episode))

    for imdb_url, showinfo in trakt_watchlist_shows.items():
        if imdb_url in current_shows:
            continue

        if imdb_url not in imdb_show_map:
            show = re.sub('[^A-Za-z0-9 ]', '', showinfo.title).lower().replace(' ', '_')
            mq_.imdb_ratings[show] = ti_.get_imdb_rating(show, imdb_url)
            print(mq_.imdb_ratings[show])
        else:
            show = imdb_show_map[imdb_url]

        if search and any(x not in show for x in search):
            continue

        current_shows.add(imdb_url)
        if imdb_url not in imdb_show_map:
            imdb_show_map[imdb_url] = show
        max_season[imdb_url] = -1
        max_episode[imdb_url][-1] = -1

    for imdb_url in current_shows:
        if imdb_url in trakt_watched_shows:
            for s, e in sorted(trakt_watched_shows[imdb_url]):
                max_s = max_season.get(imdb_url, -1)
                max_e = max_episode.get(imdb_url, {}).get(s, -1)
                max_season[imdb_url] = max(s, max_s)
                max_episode[imdb_url][s] = max(e, max_e)
                current_seasons[imdb_url].add(s)
                current_episodes[imdb_url].add((s, e))

    for imdb_url in sorted(current_shows):
        show = imdb_show_map[imdb_url]
        max_s = max_season[imdb_url]
        max_e = max_episode[imdb_url][max_s]
        title = mq_.imdb_ratings[show]['title']
        rating = mq_.imdb_ratings[show]['rating']
        if imdb_url == '':
            continue
        if do_update:
            for item in parse_imdb_episode_list(imdb_url, season=-1):
                season = item[0]
                if season < max_s:
                    continue
                mq_.get_imdb_episode_ratings(show, season)
        for season, episode in sorted(mq_.imdb_episode_ratings[show]):
            row = mq_.imdb_episode_ratings[show][(season, episode)]
            if season < max_s:
                continue
            if episode <= max_episode[imdb_url].get(season, -1):
                continue
            if not search and row['airdate'] < (maxdate - datetime.timedelta(days=10)):
                continue
            if row['airdate'] > maxdate:
                continue
            if (season, episode) in current_episodes[imdb_url]:
                continue
            eptitle = row['eptitle']
            eprating = row['rating']
            airdate = row['airdate']
            output[(airdate, show)] = '%s %s %s %d %d %0.2f/%0.2f %s' % (
                        show, title, eptitle, season, episode, eprating, rating, airdate)
    for key in sorted(output):
        val = output[key]
        print(val)


def find_new_episodes_watchlist(search=(), do_update=False):
    output = {}
    mq_ = MovieCollection()

    current_shows = set()
    max_season = {}
    max_episode = defaultdict(dict)
    current_seasons = defaultdict(set)
    current_episodes = defaultdict(set)
    for fname, row in mq_.movie_collection.items():
        show = row['show']
        cond0 = (show in watchlist)
        cond1 = all(x in show for x in search)
        if search and not cond1:
            continue
        if not search and not cond0:
            continue
        fname = row['path']
        season, episode = mq_.get_season_episode_from_name(fname, show)
        if season == -1 or episode == -1:
            continue
        max_s = max_season.get(show, -1)
        max_e = max_episode.get(show, {}).get(season, -1)
        current_shows.add(show)
        max_season[show] = max(max_s, season)
        max_episode[show][season] = max(max_e, episode)
        current_seasons[show].add(season)
        current_episodes[show].add((season, episode))

    for show in sorted(current_shows):
        max_s = max_season[show]
        max_e = max_episode[show][max_s]
        imdb_url = mq_.imdb_ratings[show]['link']
        title = mq_.imdb_ratings[show]['title']
        rating = mq_.imdb_ratings[show]['rating']
        if do_update:
            for item in parse_imdb_episode_list(imdb_url, season=-1):
                season = item[0]
                if season < max_s:
                    continue
                mq_.get_imdb_episode_ratings(show, season)
        for season, episode in sorted(
                mq_.imdb_episode_ratings[show], key=lambda x: x[0] * 100 + x[1]):
            row = mq_.imdb_episode_ratings[show][(season, episode)]
            if season < max_s:
                continue
            if season in max_episode[show] \
                    and episode <= max_episode[show][season]:
                continue

#            if row['airdate'] > datetime.date.today():
#                continue
            if (season, episode) in current_episodes:
                continue
            eptitle = row['eptitle']
            eprating = row['rating']
            airdate = row['airdate']
            output[(airdate,
                    show)] = '%s %s %d %d %s %0.2f/%0.2f %s' % (show, title, season, episode,
                                                                eptitle, eprating, rating, airdate)
    for key in sorted(output):
        val = output[key]
        print(val)

    return


def find_new_episodes_parse():
    parser = argparse.ArgumentParser(description='find_new_episodes script')
    parser.add_argument('command', nargs='*', help=help_text)
    args = parser.parse_args()

    _command = 'list'
    do_update = False
    _args = []

    if hasattr(args, 'command'):
        for arg in args.command:
            if arg in list_of_commands:
                _command = arg
            elif arg == 'update':
                do_update = True
            else:
                _args.append(arg)

    if _command == 'wl':
        find_new_episodes_watchlist(_args, do_update)
    elif _command == 'tv':
        find_upcoming_episodes(do_update=do_update)
    else:
        find_new_episodes(_args, do_update)
