#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 20:44:24 2016

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import glob
import time
from movie_collection_app.movie_collection import MovieCollection


def sync_queue_with_nas(run_command=True):
    mq_ = MovieCollection()
    for row in mq_.current_queue:
        fname = row['path']
        if 'sabrent2000' not in fname:
            continue
        if '.mp4' not in fname:
            continue
        nasname = fname.replace('sabrent2000', 'dileptonnas')
        nasname = nasname.replace('movies/television', 'television')
        naspath = '/'.join(nasname.split('/')[:-1])
        if not os.path.exists(naspath):
            cmd = 'mkdir -p %s' % naspath
            print(cmd)
            if run_command:
                os.system(cmd)
        if 'sabrent2000' in fname and not os.path.exists(nasname):
            cmd = 'cp -n %s %s' % (fname, nasname)
            print(cmd)
            if run_command:
                os.system(cmd)
            cmd = 'md5sum %s %s' % (fname, nasname)
            print(cmd)
            if run_command:
                os.system(cmd)
                time.sleep(1)
    return


def sync_sabrent_with_nas(run_command=True):
    naspath = '/media/dileptonnas/Documents/television'
    sabpath = '/media/sabrent2000/Documents/movies/television'
    dirs = [x.split('/')[-1] for x in glob.glob('%s/*' % naspath)]
    for d in dirs:
        fpath = '%s/%s' % (sabpath, d)
        if not os.path.exists(fpath):
            continue
        seasons = [x.split('/')[-1] for x in glob.glob('%s/*' % fpath)]
        for season in seasons:
            sabfiles = [x.split('/')[-1]
                        for x in glob.glob('%s/%s/%s/*.mp4'
                                           % (sabpath, d, season))]
            for f in sabfiles:
                sabfile = '%s/%s/%s/%s' % (sabpath, d, season, f)
                nasfile = '%s/%s/%s/%s' % (naspath, d, season, f)
                if not os.path.exists('%s/%s/%s' % (naspath, d, season)):
                    cmd = 'mkdir -p %s/%s/%s' % (naspath, d, season)
                    print(cmd)
                    if run_command:
                        os.system(cmd)
                if not os.path.exists(nasfile):
                    cmd = 'cp %s %s' % (sabfile, nasfile)
                    print(cmd)
                    if run_command:
                        os.system(cmd)
                    cmd = 'md5sum %s %s' % (sabfile, nasfile)
                    print(cmd)
                    if run_command:
                        os.system(cmd)
                        time.sleep(1)
    dirs = [x.split('/')[-1] for x in glob.glob('%s/*' % sabpath)]
    for d in dirs:
        fpath = '%s/%s' % (sabpath, d)
        if not os.path.exists(fpath):
            continue
        seasons = [x.split('/')[-1] for x in glob.glob('%s/*' % fpath)]
        for season in seasons:
            sabfiles = [x.split('/')[-1]
                        for x in glob.glob('%s/%s/%s/*.mp4'
                                           % (sabpath, d, season))]
            for f in sabfiles:
                sabfile = '%s/%s/%s/%s' % (sabpath, d, season, f)
                nasfile = '%s/%s/%s/%s' % (naspath, d, season, f)
                if not os.path.exists('%s/%s/%s' % (naspath, d, season)):
                    cmd = 'mkdir -p %s/%s/%s' % (naspath, d, season)
                    print(cmd)
                    if run_command:
                        os.system(cmd)
                if not os.path.exists(nasfile):
                    cmd = 'cp %s %s' % (sabfile, nasfile)
                    print(cmd)
                    if run_command:
                        os.system(cmd)
                    cmd = 'md5sum %s %s' % (sabfile, nasfile)
                    print(cmd)
                    if run_command:
                        os.system(cmd)
                        time.sleep(1)
    naspath = '/media/dileptonnas/Documents/movies'
    sabpath = '/media/sabrent2000/Documents/movies'
    dirs = ('adult', 'foreign', 'horror', 'documentary', 'scifi', 'comedy',
            'drama', 'action')
    for d in dirs:
        fpath = '%s/%s' % (sabpath, d)
        if not os.path.exists(fpath):
            continue
        movies = [x.split('/')[-1] for x in glob.glob('%s/*.mp4' % fpath)]
        for f in movies:
            sabfile = '%s/%s/%s' % (sabpath, d, f)
            nasfile = '%s/%s/%s' % (naspath, d, f)
            if not os.path.exists('%s/%s' % (naspath, d)):
                cmd = 'mkdir -p %s/%s' % (naspath, d)
                print(cmd)
                if run_command:
                    os.system(cmd)
            if not os.path.exists(nasfile):
                cmd = 'cp %s %s' % (sabfile, nasfile)
                print(cmd)
                if run_command:
                    os.system(cmd)
                cmd = 'md5sum %s %s' % (sabfile, nasfile)
                print(cmd)
                if run_command:
                    os.system(cmd)
                    time.sleep(1)


def remove_leftover_avi(run_command=False):
    naspath = '/media/dileptonnas/Documents/television'
    sabpath = '/media/sabrent2000/Documents/movies/television'
    dirs = [x.split('/')[-1] for x in glob.glob('%s/*' % sabpath)]
    for d in dirs:
        fpath = '%s/%s' % (sabpath, d)
        if not os.path.exists(fpath):
            continue
        seasons = [x.split('/')[-1] for x in glob.glob('%s/*' % fpath)]
        for season in seasons:
            sabfiles = [x.split('/')[-1]
                        for x in glob.glob('%s/%s/%s/*.mp4'
                                           % (sabpath, d, season))]
            for f in sabfiles:
                nasfile = '%s/%s/%s/%s' % (naspath, d, season, f)
                nasfile = nasfile.replace('.mp4', '.mkv')
                if os.path.exists(nasfile):
                    print(nasfile)
                    if run_command:
                        os.remove(nasfile)
