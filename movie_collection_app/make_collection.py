#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 23:56:17 2016

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import argparse

from movie_collection_app.movie_collection import MovieCollection
from movie_collection_app.util import (walk_wrapper, read_time, print_h_m_s)

file_formats = ('mp4', 'mkv', 'avi')
list_of_commands = ('parse', 'list', 'time', 'mov')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)
movie_dirs = ('/media/dileptonnas/Documents/movies',
              '/media/dileptonnas/Documents/television',
              '/media/dileptonnas/television/unwatched',
              #'/media/sabrent2000/television/unwatched',
              #'/media/sabrent2000/Documents/movies',
              #'/media/sabrent2000/Documents/television',
              '/media/western2000/Documents/movies',)


def make_collection():
    all_files = set()
    all_shows = set()

    mq_ = MovieCollection()

    def parse_dir(_, path, filelist):
        for fname in filelist:
            fullpath = '%s/%s' % (path, fname)
            if os.path.isdir(fullpath):
                continue
            if not any(fname.endswith(x) for x in file_formats):
                continue
            all_files.add(fullpath)
            if fullpath in mq_.movie_collection:
                all_shows.add(mq_.movie_collection[fullpath]['show'])
                continue
            print(fullpath)
            mq_.add_entry_to_collection(fullpath)
            all_shows.add(mq_.movie_collection[fullpath]['show'])

    for dir_ in movie_dirs:
        walk_wrapper(dir_, parse_dir, None)

    fnames = mq_.movie_collection.keys()

    print(len(all_files), len(all_shows), len(mq_.movie_collection))

    for fname in fnames:
        if fname in all_files:
            continue
        if 'caviar2000' in fname or 'sabrent2000' in fname:
            continue
        print('file %s not on disk' % fname)
        mq_.rm_entry_from_collection(fname)

    for show in mq_.imdb_ratings:
        if show in all_shows:
            continue
        rating_obj = mq_.imdb_ratings.get(show, None)
        if rating_obj:
            print('show %s not on disk: %s %s' % (
                show, mq_.imdb_ratings[show]['rating'],
                mq_.imdb_ratings[show]['title']))
#            mq_.rm_entry_from_ratings(show)

    print(len(mq_.imdb_ratings), len(mq_.imdb_episode_ratings))


def search_collection(search_strs, do_time=False):
    output_str = []
    mq_ = MovieCollection()

    for path in mq_.movie_collection:
        if 'caviar2000' in path or 'sabrent2000' in path:
            continue
        if any(x in path for x in search_strs):
            path_ = mq_.movie_collection[path]['path']
            show_ = mq_.movie_collection[path]['show']
            imdb_ = mq_.imdb_ratings.get(show_, None)
            if not imdb_:
                imdb_ = mq_.get_imdb_rating(path_)
            title_ = imdb_['title']
            rating_ = imdb_['rating']
            imdb_str = '%s %s' % (rating_, title_)
            time_str = ''
            season, episode = -1, -1
            if imdb_['istv']:
                tmp = mq_.get_season_episode_from_name(path_, show_)
                season, episode = tmp
                if season >= 0 and episode >= 0:
                    imdb_ = mq_.imdb_episode_ratings.get(show_, {})\
                                                    .get((season, episode),
                                                         imdb_)
                    if 'eptitle' in imdb_:
                        imdb_str = '%s/%s s%02d ep%02d %s %s' % (
                            imdb_['rating'], rating_, season, episode, title_,
                            imdb_['eptitle'])
            if do_time:
                time_ = read_time(path_)
                if time_ > 0:
                    time_str = print_h_m_s(time_)
            tmp = [path_, show_, imdb_str]
            if time_str:
                tmp.insert(1, time_str)
            output_str.append(' '.join(tmp))
    return sorted(output_str)


def make_collection_parse():
    parser = argparse.ArgumentParser(description='make_collection script')
    parser.add_argument('command', nargs='*', help=help_text)
    args = parser.parse_args()

    _command = 'parse'
    _args = []

    if hasattr(args, 'command'):
        if len(args.command) > 0:
            _command = args.command[0]
            if _command not in list_of_commands:
                try:
                    _command = int(_command)
                except ValueError:
                    print(help_text)
                    exit(0)
        if len(args.command) > 1:
            for it_ in args.command[1:]:
                try:
                    it_ = int(it_)
                except ValueError:
                    pass
                _args.append(it_)

    if _command == 'parse':
        make_collection()
    if _command == 'list' or _command == 'time':
        out_list = search_collection(_args, do_time=(_command == 'time'))
        if len(out_list) > 0:
            print('\n'.join(out_list))
