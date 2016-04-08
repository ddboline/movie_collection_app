#!/usr/bin/python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import argparse
import datetime
from collections import defaultdict

from movie_collection_app.movie_collection import MovieCollection
from movie_collection_app.parse_imdb import parse_imdb_episode_list
from movie_collection_app.util import get_season_episode_from_name

list_of_commands = ('list', 'search', 'wl')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)
watchlist = {'12_monkeys', 'adventure_time', 'american_crime_story', 'archer',
             'homeland', 'game_of_thrones', 'the_expanse', 'colony',
             'star_wars_rebels', 'orphan_black', 'lost_girl',
             'man_seeking_woman', 'the_good_wife', 'the_last_ship',
             'the_leftovers', 'rick_and_morty','vikings'
             'last_week_tonight_with_john_oliver'}


def find_new_episodes(search=(), do_update=False):
    output = {}
    mq_ = MovieCollection()

    current_shows = set()
    max_season = {}
    max_episode = defaultdict(dict)
    current_seasons = defaultdict(set)
    current_episodes = defaultdict(set)
    for row in mq_.current_queue:
        show = row['show']
        if search and any(x not in show for x in search):
            continue
        fname = row['path']
        season, episode = get_season_episode_from_name(fname, show)
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
#        print(show, max_s, max_e)
        imdb_link = mq_.imdb_ratings[show]['link']
        title = mq_.imdb_ratings[show]['title']
        rating = mq_.imdb_ratings[show]['rating']
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
            if row['airdate'] > datetime.date.today():
                continue
            if (season, episode) in current_episodes:
                continue
            eptitle = row['eptitle']
            eprating = row['rating']
            airdate = row['airdate']
            output[(airdate, show)] = '%s %s %s %d %d %0.2f/%0.2f %s' % (
                show, title, eptitle, season, episode, eprating, rating,
                airdate)
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
        season, episode = get_season_episode_from_name(fname, show)
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
        for season, episode in sorted(mq_.imdb_episode_ratings[show]):
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
            output[(airdate, show)] = '%s %s %s %d %d %0.2f/%0.2f %s' % (
                show, title, eptitle, season, episode, eprating, rating,
                airdate)
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
