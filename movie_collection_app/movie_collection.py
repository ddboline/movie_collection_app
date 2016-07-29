#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 19:52:44 2016

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import re
import random
from collections import defaultdict
from sqlalchemy import create_engine
from subprocess import call

from movie_collection_app.parse_imdb import (parse_imdb_mobile_tv, parse_imdb,
                                             parse_imdb_episode_list)
from movie_collection_app.util import (
    POSTGRESTRING, HOSTNAME, extract_show, get_season_episode_from_name,
    remove_remote_file, has_been_downloaded, get_remote_file, read_time,
    print_h_m_s, play_file, get_dailies_airdate, dailies)


class MovieCollection(object):
    ''' class containing movie queue '''
    def __init__(self,
                 queue_file='/home/ddboline/Dropbox/backup/current_queue.txt',
                 collection_dir='/home/ddboline/Dropbox/movie_collection'):
        self.queue_file = queue_file
        self.collection_dir = collection_dir
        self.movie_collection = {}
        self.current_queue = []
        self.queue_dict = {}
        self.imdb_ratings = {}
        self.imdb_episode_ratings = defaultdict(dict)
        self.eng = create_engine('%s:5432/movie_queue' % POSTGRESTRING)
        self.con = self.eng.connect()
        self.read_queue_from_db()
        self.read_imdb_ratings()
        self.read_imdb_episodes()

    def read_queue_from_db(self):
        self.movie_collection = {}
        for row in self.con.execute("select * from movie_collection"):
            row_dict = {x: row[x] for x in ('idx', 'path', 'show')}
            self.movie_collection[row_dict['path']] = row_dict
        self.current_queue = []
        for idy, row in enumerate(self.con.execute(
                'select * from current_queue order by idx')):
            row_dict = {x: row[x] for x in ('index', 'idx', 'path', 'show')}
            row_dict['idy'] = idy
            self.current_queue.append(row_dict)
            self.queue_dict[row['path']] = row_dict

    def write_queue_to_db(self):
        for idy, row in enumerate(self.current_queue):
            fname = row['path']
            show = row['show']
            index = row['index']
            self.queue_dict[fname]['idx'] = idy
            self.con.execute(
                "insert into current_queue (index, idx, path, show) values "
                "(%d, %d, '%s', '%s')" % (index, idy, fname, show))

    def fix_index(self):
        for idy, row in enumerate(self.current_queue):
            if row['idx'] != idy:
                self.con.execute("update current_queue set idx = %d "
                                 "where path = '%s'" % (idy, row['path']))

    def read_imdb_ratings(self):
        for row in self.con.execute("select * from imdb_ratings"):
            self.imdb_ratings[row['show']] = dict(row)

    def read_imdb_episodes(self):
        for row in self.con.execute("select * from imdb_episodes"):
            show = row['show']
            season = row['season']
            episode = row['episode']
            self.imdb_episode_ratings[show][(season, episode)] = dict(row)

    def get_imdb_rating(self, fn_):
        show, type_ = extract_show(fn_)
        if show in self.imdb_ratings:
            return self.imdb_ratings[show]
        show_ = show.replace('_', ' ')
        title = None
        if type_ == 'tv':
            title, imdb_link, rating = parse_imdb_mobile_tv(show_)
        else:
            for title, imdb_link, rating in parse_imdb(show_):
                if 'TV Series' not in title and 'TV Mini-Series' not in title:
                    break
        if title is None:
            return {'show': show, 'title': title, 'link': None,
                    'rating': -1, 'istv': False, 'index': -1}
        title = title.replace("'", '')
        print(show, title, imdb_link, rating)
        idx = list(self.con.execute("select max(index) from imdb_ratings"))
        idx = idx[0][0]
        row_dict = {'show': show, 'title': title, 'link': imdb_link,
                    'rating': rating, 'istv': type_ == 'tv', 'index': idx+1}
        self.imdb_ratings[show] = row_dict
        keys, vals = zip(*row_dict.items())
        self.con.execute("insert into imdb_ratings (%s) values ('%s')"
                         % (', '.join(keys),
                            "', '".join('%s' % x for x in vals)))
        return self.imdb_ratings[show]

    def get_imdb_episode_ratings(self, show=None, season=None):
        """ dump all episode ratings for a given show, store in db """
        for show_ in self.imdb_ratings:
            if show is not None and show_ != show:
                continue
            if not show and show_ in self.imdb_episode_ratings:
                continue
            if not self.imdb_ratings[show_]['istv']:
                continue
            url = self.imdb_ratings[show_]['link']
            if not url:
                continue
            idx = list(self.con.execute("SELECT max(id) FROM imdb_episodes"))
            idx = idx[0][0]
            if idx is None:
                idx = 0
            else:
                idx += 1
            epi_rating_items = []
            print(show_, url)
            for item in parse_imdb_episode_list(imdb_id=url, season=-1):
                season_ = item[0]
                if all(x is not None for x in (show, season)) \
                        and season_ != season:
                    continue
                for item in parse_imdb_episode_list(imdb_id=url,
                                                    season=season_):
                    se_, epi, ad_, rt_, eti, eurl = item
                    itdict = {'id': idx, 'show': show_, 'season': se_,
                              'episode': epi, 'epurl': eurl, 'airdate': ad_,
                              'rating': rt_, 'eptitle': eti}
                    epi_rating_items.append(itdict)
                    #print(itdict)
                    idx += 1
            for itdict in epi_rating_items:
                season_ = itdict['season']
                episode_ = itdict['episode']
                epurl_ = itdict['epurl']
                rating_ = itdict['rating']
                airdate_ = itdict['airdate']
                eptitle_ = re.sub('[^A-Za-z0-9 ]', '', itdict['eptitle'])
                itdict['eptitle'] = eptitle_
                tmp = self.imdb_episode_ratings.get(show, {})
                if tmp and tmp.get((season_, episode_), {}):
                    self.con.execute(
                        "UPDATE imdb_episodes SET "
                        "rating=%d,epurl='%s',airdate='%s',eptitle='%s' "
                        "WHERE show='%s' and season=%d "
                        "and episode = %d" % (rating_, epurl_, airdate_,
                                              eptitle_, show, season_,
                                              episode_))
                else:
                    keys, values = zip(*itdict.items())
                    keys = ', '.join('%s' % x for x in keys)
                    values = "', '".join('%s' % x for x in values)
                    self.con.execute('INSERT INTO imdb_episodes '
                                     "(%s) VALUES ('%s')" % (keys, values))

    def get_season_episode_rating_from_name(self, fname):
        ratings = self.get_imdb_rating(fname)
        show, link = [ratings.get(x) for x in 'show', 'link']
        season, episode = get_season_episode_from_name(fname, show)
        if season == -1 and episode == -1 and show in dailies:
            airdate_ = get_dailies_airdate(fname, show)
            if show in self.imdb_episode_ratings \
                    and self.imdb_episode_ratings[show]:
                season = max(k[0] for k in self.imdb_episode_ratings[show])
            else:
                season = list(parse_imdb_episode_list(link, season=-1))[-1][0]
            tmp = [k for k, v in self.imdb_episode_ratings[show].items()
                   if k[0] == season and v['airdate'] == airdate_]
            if len(tmp) == 0:
                #print(fname, airdate_)
                return show, link, -1, -1
            episode = tmp[0][1]
        if show not in self.imdb_episode_ratings:
            self.get_imdb_episode_ratings(show, season=season)
        elif (season, episode) not in self.imdb_episode_ratings[show]:
            self.get_imdb_episode_ratings(show, season=season)
        elif show not in dailies and (
                self.imdb_episode_ratings.get(show)
                                         .get((season, episode))
                                         .get('rating') < 0):
            self.get_imdb_episode_ratings(show, season=season)
        return show, link, season, episode

    def get_season_episode_from_name(self, fname, show):
        if show in dailies:
            tmp = self.get_season_episode_rating_from_name(fname)
            show, link, season, episode = tmp
            return season, episode
        else:
            return get_season_episode_from_name(fname, show)

    def add_entry(self, fname, position=-1):
        ''' add entry to queue '''
        if position < 0:
            position = len(self.current_queue)
        if fname in self.queue_dict:
            row = self.queue_dict[fname]
            curpos = row['idy']
            print(position, curpos, row['idx'], row['idy'], fname)
            if position < curpos:
                self.con.execute(
                    "update current_queue set idx = '%d' where path = '%s'"
                    % (position, fname))
                self.con.execute(
                    "update current_queue set idx = idx + 1 where "
                    "idx >= %d and idx < %d and path != '%s'"
                    % (position, curpos, fname))
            elif position != curpos:
                self.con.execute(
                    "update current_queue set idx = %d where path = '%s'"
                    % (position, fname))
                self.con.execute(
                    "update current_queue set idx = idx - 1 where "
                    "idx > %d and idx <= %d and path != '%s'"
                    % (curpos, position, fname))
                print(position, fname)
        else:
            show, link, _, _ = self.get_season_episode_rating_from_name(fname)
            new_index = max(x['index'] for x in self.current_queue) + 1
            row_dict = {'idx': position, 'path': fname, 'show': show,
                        'link': link, 'index': new_index}
            self.current_queue.insert(position, row_dict)
            self.queue_dict[fname] = row_dict
            self.con.execute(
                "insert into current_queue (index, idx, path, show) values "
                "(%d, %d, '%s', '%s')" % (new_index, position, fname, show))
            self.con.execute("update current_queue set idx = idx + 1 "
                             "where idx >= %d and path != '%s'"
                             % (position, fname))
            if fname not in self.movie_collection:
                idx_ = list(self.con.execute(
                    "select max(idx) from movie_collection"))[0][0]
                if idx_ is None:
                    idx_ = 0
                else:
                    idx_ += 1
                self.con.execute(
                    "insert into movie_collection (idx, path, show) values "
                    "(%d, '%s', '%s')" % (idx_, fname, show))
        self.read_queue_from_db()
        self.read_imdb_ratings()
        self.read_imdb_episodes()
        return ['add %s to queue at %d' % (fname, position)], 1

    def rm_entry(self, position, purge=False):
        ''' remove entry from queue '''
        remove_remote_file(self.current_queue[position]['path'])
        try:
            tmp_val = self.current_queue.pop(position)
            self.con.execute("delete from current_queue where idx = %d"
                             % tmp_val['idx'])
            self.con.execute("update current_queue set idx = idx - 1 "
                             "where idx > %d" % tmp_val['idx'])
        except IndexError:
            return []
        out_list = ['rm %s from queue' % tmp_val['path']]
        if purge and HOSTNAME == 'dilepton-tower':
            call('rm %s' % tmp_val['path'], shell=True)
            out_list += ['delete %s' % (tmp_val['path'])]
        return out_list

    def add_entry_to_collection(self, fname):
        if fname in self.movie_collection:
            return
        show, link, _, _ = self.get_season_episode_rating_from_name(fname)
        idx_ = list(self.con.execute(
            "select max(idx) from movie_collection"))[0][0]
        if idx_ is None:
            idx_ = 0
        else:
            idx_ += 1
        self.con.execute(
            "insert into movie_collection (idx, path, show) values "
            "(%d, '%s', '%s')" % (idx_, fname, show))
        row_dict = {'idx': idx_, 'path': fname, 'show': show}
        self.movie_collection[row_dict['path']] = row_dict

        self.read_imdb_ratings()
        self.read_imdb_episodes()
        return ['add %s to collection at %d' % (fname, idx_)], 1

    def rm_entry_from_collection(self, fname):
        if fname not in self.movie_collection:
            return
        self.con.execute("delete from movie_collection where path='%s'"
                         % fname)
        self.movie_collection.pop(fname)

    def rm_entry_from_ratings(self, show):
        if show not in self.imdb_ratings:
            return
        self.con.execute("delete from imdb_ratings where show='%s'" % show)

    def rm_entry_from_episodes(self, show, season=-1, episode=-1):
        if show not in self.imdb_episode_ratings:
            return
        if season == -1 and episode == -1:
            self.con.execute("delete from imdb_episodes where show='%s'"
                             % show)
            self.imdb_episode_ratings.pop(show)
        elif episode == -1:
            self.con.execute(
                "delete from imdb_episodes where show='%s' and season=%d"
                % (show, season))
            for (season_, episode_) in self.imdb_episode_ratings[show]:
                if season_ == season:
                    self.imdb_episode_ratings[show].pop((season_, episode_))
        else:
            if (season, episode) not in self.imdb_episode_ratings[show]:
                return
            self.con.execute(
                "delete from imdb_episodes "
                "where show='%s' and season=%d and episode=%d"
                % (show, season, episode))
            self.imdb_episode_ratings[show].pop((season, episode))

    def show_entry_by_name(self, name):
        ''' return entry in queue containing name '''
        for row in self.current_queue:
            fn_ = row['path']
            if name in fn_:
                return fn_
        return ''

    def get_entry_by_name(self, name):
        ''' return entry if it exists locally, if not download from remote '''
        for row in self.current_queue:
            fn_ = row['path']
            if name in fn_:
                if has_been_downloaded(fn_):
                    continue
                else:
                    return get_remote_file(fn_)
        return ''

    def rm_entry_by_name(self, name, purge=False):
        ''' remove entry from queue, delete local copy if exists '''
        for bidx, row in enumerate(self.current_queue):
            fn_ = row['path']
            if name in fn_:
                return self.rm_entry(bidx, purge)
        return ''

    def entry_string(self, idx, do_time=False):
        ''' return formatted string for a given entry '''
        fname = self.current_queue[idx]['path']
        show = self.current_queue[idx]['show']
        if show in self.imdb_episode_ratings:
            row = self.imdb_episode_ratings[show]
            season, episode = get_season_episode_from_name(fname, show)
            row = row.get((season, episode), {})
            link = row.get('epurl', '')
        elif show in self.imdb_ratings:
            link = self.imdb_ratings[show].get('link', '')
        else:
            link = ''
        out_list = []
        if not do_time:
            out_list += ['%4d %s %s' % (idx, fname, link)]
        else:
            tm_ = read_time(fname)
            if tm_ > 0:
                out_list += ['%4d %s %s %s' % (idx, print_h_m_s(tm_), fname,
                                               link)]
        return out_list

    def entry_string_collection(self, fn_, do_time=False):
        ''' return formatted string for a given entry '''
        fname = self.movie_collection[fn_]['path']
        show = self.movie_collection[fn_]['show']
        if show in self.imdb_episode_ratings:
            row = self.imdb_episode_ratings[show]
            season, episode = get_season_episode_from_name(fname, show)
            row = row.get((season, episode), {})
            link = row.get('epurl', '')
        elif show in self.imdb_ratings:
            link = self.imdb_ratings[show].get('link', '')
        else:
            link = ''
        out_list = []
        if not do_time:
            out_list += ['%s %s' % (fname, link)]
        else:
            tm_ = read_time(fname)
            if tm_ > 0:
                out_list += ['%s %s %s' % (print_h_m_s(tm_), fname, link)]
        return out_list

    def list_entries(self, name=None, first_entry=0, last_entry=0,
                     do_time=False, do_local=False):
        ''' list entries satisfying name or index '''
        if last_entry == 0:
            last_entry = len(self.current_queue)
        out_list = []
        for ent in self.current_queue[first_entry:last_entry]:
            idx = self.current_queue.index(ent)
            ent = ent['path']
            fn_ = ent.split('/')[-1]
            if not name:
                if not do_local:
                    out_list += self.entry_string(idx, do_time)
                elif do_local and HOSTNAME == 'dilepton-tower':
                    out_list += self.entry_string(idx, do_time)
                elif do_local and has_been_downloaded(ent):
                    out_list += self.entry_string(idx, do_time)
            elif name in fn_:
                out_list += self.entry_string(idx, do_time)
        return out_list

    def list_entries_from_collection(self, name=None, do_time=False,
                                     do_local=False):
        out_list = []
        for key, ent in self.movie_collection.items():
            ent = ent['path']
            fn_ = ent.split('/')[-1]
            if not name:
                if not do_local:
                    out_list += self.entry_string_collection(fn_, do_time)
                elif do_local and HOSTNAME == 'dilepton-tower':
                    out_list += self.entry_string_collection(fn_, do_time)
                elif do_local and has_been_downloaded(ent):
                    out_list += self.entry_string_collection(fn_, do_time)
            elif name in fn_:
                out_list += self.entry_string_collection(fn_, do_time)
        return out_list

    def list_tvshows(self, do_random=False, play_random=False):
        ''' list television shows '''
        tvshows = defaultdict(int)
        imdb_link = {}
        out_list = []
        for row in self.current_queue:
            ent = row['path']
            if 'television' not in ent:
                continue
            show = ent.split('television/')[1].split('/')[0]
            if show == 'unwatched':
                show = ent.split('television/unwatched/')[1]
                for spl in (r'_s\d+_', r'_201\d+?'):
                    show = re.split(spl, show)[0]
            tvshows[show] += 1
            imdb_link[show] = self.imdb_ratings.get('link', '')
        list_of_tvshows = sorted(tvshows.keys())
        if do_random:
            random.seed(os.urandom(16))
            idx = random.randint(0, len(list_of_tvshows)-1)
            tvshow = list_of_tvshows[idx]
            out_list += ['%s' % (tvshow)]
            if play_random:
                fn_ = self.show_entry_by_name(tvshow)
                if fn_:
                    print(fn_)
                    play_file(fn_, rmt=False)
        else:
            for show in list_of_tvshows:
                out_list += ['%-30s %3d %10s' % (show, tvshows[show],
                                                 imdb_link[show])]
        return out_list
