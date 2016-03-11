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
from movie_collection_app.util import (walk_wrapper,
                                       get_season_episode_from_name)

file_formats = ('mp4', 'mkv', 'avi')
list_of_commands = ('parse', 'list', 'time', 'mov')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)
movie_dirs = ('/media/sabrent2000/Documents/movies',
              '/media/caviar2000/Documents/movies',
              '/media/nexstarext4/Documents/movies',
              '/media/sabrent2000/television/unwatched',
              '/media/western2000/Documents/movies',
              '/media/western2000/television/unwatched')


def make_collection():
    mq_ = MovieCollection()

    def parse_dir(_, path, filelist):
        for fname in filelist:
            fullpath = '%s/%s' % (path, fname)
            print(fullpath)
            if os.path.isdir(fullpath):
                continue
            if not any(fname.endswith(x) for x in file_formats):
                continue
            mq_.add_entry_to_collection(fullpath)

    for dir_ in movie_dirs:
        walk_wrapper(dir_, parse_dir, None)


def search_collection(search_strs):
    output_str = []
    mq_ = MovieCollection()

    for path in mq_.movie_collection:
        if any(x in path for x in search_strs):
            path_ = mq_.movie_collection[path]['path']
            show_ = mq_.movie_collection[path]['show']
            imdb_ = mq_.imdb_ratings[show_]
            title_ = imdb_['title']
            rating_ = imdb_['rating']
            imdb_str = '%s %s' % (rating_, title_)
            season, episode = -1, -1
            if imdb_['istv']:
                season, episode = get_season_episode_from_name(path_, show_)
                if season >= 0 and episode >= 0:
                    imdb_ = mq_.imdb_episode_ratings.get(show_, {})\
                                                    .get((season, episode),
                                                         imdb_)
                    imdb_str = '%s/%s s%02d ep%02d %s %s' % (imdb_['rating'],
                                                             rating_, season,
                                                             episode, title_,
                                                             imdb_['eptitle'])
            output_str.append(' '.join((path_, show_, imdb_str)))
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
    if _command == 'list':
        out_list = search_collection(_args)
        if len(out_list) > 0:
            print('\n'.join(out_list))
