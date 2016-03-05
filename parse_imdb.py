#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 20:53:07 2016

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os

from movie_collection_app.movie_collection import MovieCollection
from movie_collection_app.parse_imdb import (parse_imdb_mobile_tv,
                                             parse_imdb_episode_list,
                                             parse_imdb)


if __name__ == '__main__':
    name = []
    do_tv = False
    season = None
    for arg in os.sys.argv:
        if arg == 'tv':
            do_tv = True
        elif 'season=' in arg:
            tmp = arg.replace('season=', '')
            try:
                season = int(tmp)
            except ValueError:
                pass
            continue
        elif 'parse_imdb' in arg or 'python' in arg:
            continue
        else:
            name.append(arg.replace('_', ' '))

    name = ' '.join(name)

    mc_ = MovieCollection()

    if do_tv:
        title, imdb_link, rating = parse_imdb_mobile_tv(name)
        show_ = ''
        for show, val in mc_.imdb_ratings.items():
            if val['link'] == imdb_link:
                show_ = show
                break
        print(title, imdb_link, rating)
        if season == -1:
            for item in parse_imdb_episode_list(imdb_link, season=season):
                season_, episode, airdate, ep_rating, ep_title, ep_url = item
                print(title, season_)
        mc_.get_imdb_episode_ratings(show=show_, season=season)
        for (season_, episode) in sorted(mc_.imdb_episode_ratings[show_]):
            if season and season != season_:
                continue
            row = mc_.imdb_episode_ratings[show_][(season_, episode)]
            airdate = row['airdate']
            ep_rating = row['rating']
            ep_title = row['eptitle']
            print(title, season_, episode, airdate, ep_rating, ep_title)
    else:
        for idx, (title, imdb_link, rating) in enumerate(parse_imdb(name)):
            print(idx, title, imdb_link, rating)
