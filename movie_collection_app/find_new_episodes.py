#!/usr/bin/python
from __future__ import (absolute_import, division, print_function, unicode_literals)
import argparse
import datetime
from dateutil.parser import parse
from collections import defaultdict
from sqlalchemy import create_engine
import pandas as pd

from movie_collection_app.movie_collection import MovieCollection
from movie_collection_app.parse_imdb import parse_imdb_episode_list, parse_imdb_tv_listings
from movie_collection_app.util import POSTGRESTRING

list_of_commands = ('list', 'search', 'wl')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)
watchlist = {
    '12_monkeys', 'adventure_time', 'archer', 'homeland', 'game_of_thrones', 'lost_girl',
    'mr_robot', 'rick_and_morty', 'vikings', 'last_week_tonight_with_john_oliver', 'outlander_2014',
    'silicon_valley', 'the_last_panthers', 'the_night_manager', 'fear_the_walking_dead', 'unreal'}

pg_db = '%s:5432/movie_queue' % POSTGRESTRING
engine = create_engine(pg_db)


def find_upcoming_episodes(df=None):
    if df is None:
        df = parse_imdb_tv_listings()
    with engine.connect() as db:
        query = """
            SELECT
                t1.show,
                t1.season,
                t1.episode,
                t2.link as imdb_url,
                t1.epurl as ep_url
            FROM imdb_episodes t1
            JOIN imdb_ratings t2 ON t1.show = t2.show
        """
        rating_df = pd.read_sql(query, db)
    imdb_urls = set(rating_df.imdb_url.unique())
    ep_urls = set(rating_df.ep_url.unique())
    df = df[(df.imdb_url.isin(imdb_urls)) & (-df.ep_url.isin(ep_urls))].reset_index(drop=True)

    mq_ = MovieCollection()
    max_season = {}
    current_shows = set()
    for row in mq_.current_queue:
        show = row['show']
        fname = row['path']
        season, episode = mq_.get_season_episode_from_name(fname, show)
        if season == -1 or episode == -1:
            continue
        max_s = max_season.get(show, -1)
        current_shows.add(show)
        max_season[show] = max(max_s, season)

    imdb_urls = set(df.imdb_url.unique())

    for show in sorted(current_shows):
        max_s = max_season[show]
        imdb_url = mq_.imdb_ratings[show]['link']
        if imdb_url not in imdb_urls:
            continue

        for item in parse_imdb_episode_list(imdb_url, season=-1):
            season = item[0]
            if season < max_s:
                continue
            print(show, season)
            mq_.get_imdb_episode_ratings(show, season)

    return df


def find_new_episodes(search=(), do_update=False):
    output = {}
    mq_ = MovieCollection()

    current_shows = set()
    max_season = {}
    max_episode = defaultdict(dict)
    current_seasons = defaultdict(set)
    current_episodes = defaultdict(set)
    maxdate = datetime.date.today()
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
        imdb_link = mq_.imdb_ratings[show]['link']
        title = mq_.imdb_ratings[show]['title']
        rating = mq_.imdb_ratings[show]['rating']
        if imdb_link == '':
            continue
        if do_update:
            for item in parse_imdb_episode_list(imdb_link, season=-1):
                season = item[0]
                if season < max_s:
                    continue
                mq_.get_imdb_episode_ratings(show, season)
        for season, episode in sorted(mq_.imdb_episode_ratings[show]):
            row = mq_.imdb_episode_ratings[show][(season, episode)]
            if season < max_s or season not in current_seasons[show]:
                continue
            if episode <= max_episode[show][season]:
                continue
            if row['airdate'] > maxdate:
                continue
            if (season, episode) in current_episodes:
                continue
            eptitle = row['eptitle']
            eprating = row['rating']
            airdate = row['airdate']
            output[(airdate,
                    show)] = '%s %s %s %d %d %0.2f/%0.2f %s' % (show, title, eptitle, season,
                                                                episode, eprating, rating, airdate)
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
        imdb_link = mq_.imdb_ratings[show]['link']
        title = mq_.imdb_ratings[show]['title']
        rating = mq_.imdb_ratings[show]['rating']
        if do_update:
            for item in parse_imdb_episode_list(imdb_link, season=-1):
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
    else:
        find_new_episodes(_args, do_update)
