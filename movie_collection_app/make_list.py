#! /usr/bin/env python
# -*- coding: utf-8 -*-
""" manage collection """
from __future__ import (absolute_import, division, print_function, unicode_literals)

import os
import glob
import datetime
import tempfile
import random
try:
    from util import run_command
except ImportError:
    from .util import run_command

COMMANDS = ('dvd', 'tv', 'notv', 'list', 'time', 'col', 'mov', 'dsk', 'rand', 'uniq_tv',
            'uniq_notv')

MOVIE_DIRS = (
    '/media/dileptonnas/Documents/movies',
    '/media/dileptonnas/Documents/television',
    '/media/dileptonnas/television/unwatched',
    '/media/sabrent2000/Documents/movies',
    '/media/sabrent2000/Documents/television',
    '/media/sabrent2000/television/unwatched',
    '/media/western2000/Documents/movies',
    '/media/western2000/Documents/television',
    '/media/western2000/television/unwatched',
    '/media/seagate4000/Documents/movies',
    '/media/seagate4000/Documents/television',
    '/media/seagate4000/television/unwatched',
)

HOMEDIR = os.getenv('HOME')
COLLECTION_DIR = '%s/Dropbox/movie_collection' % HOMEDIR


def make_list(tmpfile,
              do_dvd=False,
              do_collection=False,
              do_television=False,
              no_television=False,
              do_uniq=False,
              do_string=False,
              do_random=False,
              get_time=False,
              do_movies=False,
              do_disk=False,
              do_here=False,
              tv_string=None):
    """
        main function, handles input from stdin handled in main body of module
        options:
            h -- help message
            dvd -- copy list of files from a dvd, put them into movie
                   collection file
            tv -- list files in television directory that are not currently in
                  movie collection file
            notv -- list files in other directories that are not currently in
                    movie collection file
            list -- list files containing a given pattern
            time -- do list, but include duration of each file in output
            col -- list files on disk or in movie collection file matching
                   pattern
            mov -- list files in Documents/movies/
            dsk -- are files in Documents/movies/ on disk already
            rand -- random file matching pattern
            uniq_tv -- files in television that aren't also on disk or in
                       collection
            uniq_notv -- other files that aren't also on disk or in collection
    """
    _date = datetime.date.today()

    today = '%04d%02d%02d' % (_date.year, _date.month, _date.day)

    dir_ = ' '.join(MOVIE_DIRS)

    current_collection = sorted(glob.glob('%s/movie_collection_on_dvd_*.txt' % COLLECTION_DIR))[-1]

    new_collection = '%s/movie_collection_on_dvd_%s.txt' % (COLLECTION_DIR, today)

    if do_movies:
        if not do_here:
            run_command('cd %s/Documents/movies/ ; ' % HOMEDIR +
                        'for file in `ls *.avi *.mp4 *.mkv 2> /dev/null`; ' +
                        'do echo $file `find %s -iname $file 2> ' % dir_ +
                        '/dev/null | tail -n1`; done')
        else:
            run_command('for file in `ls *.avi *.mp4 *.mkv 2> /dev/null`; ' +
                        'do echo $file `find %s -iname $file ' % dir_ +
                        '2> /dev/null | tail -n1`; done')
        if not do_string:
            return 0

    if do_disk:
        if not do_here:
            run_command('cd %s/Documents/movies/ ; ' % HOMEDIR +
                        'for file in `ls *.avi *.mp4 *.mkv 2> /dev/null`; ' +
                        'do moviefile=%s; echo $file ' % current_collection +
                        '`grep $file $moviefile` ; done')
        else:
            run_command('for file in `ls *.avi *.mp4 *.mkv 2> /dev/null`; ' +
                        'do moviefile=%s; echo $file ' % current_collection +
                        '`grep $file $moviefile` ; done')
        return 0

    if do_dvd and current_collection != new_collection:
        run_command('cp %s %s' % (current_collection, new_collection))

    command = 'for file in `find %s -type f -iname \'*.avi\' ' % dir_ + \
              '2> /dev/null` `find %s -type f -iname \'*.mp4\' ' % dir_ + \
              '2> /dev/null` `find %s -type f -iname \'*.mkv\' ' % dir_ + \
              '2> /dev/null`; do du -s $file ; ' + \
              'done | awk \'{print $2,$1}\' > %s' % tmpfile.name

    if do_dvd and tv_string:
        command = 'for file in `find %s -type f ' % tv_string + \
                  '-iname \'*.avi\' 2> /dev/null` `find %s ' % tv_string + \
                  '-type f -iname \'*.mp4\' 2> /dev/null` ' + \
                  '`find %s -type f -iname \'*.mkv\' ' % tv_string + \
                  '2> /dev/null`; do du -s $file ; ' + \
                  'done | awk \'{print $2,$1}\' > %s' % tmpfile.name

    if do_collection and tv_string:
        run_command('grep %s %s' % (tv_string[0], current_collection))
    elif do_collection:
        run_command('wc -l %s' % current_collection)
        return 0

    if do_string:
        for ent in tv_string:
            command = 'find %s -type f -iname ' % dir_ + \
                      '\'*%s*.avi\' ' % ent.replace('.avi', '') + \
                      '2> /dev/null ; find %s ' % dir_ + \
                      '-type f -iname \'*%s*.mp4\' ' % ent.replace('.mp4',
                                                                   '') + \
                      '2> /dev/null ; find %s -type f ' % dir_ + \
                      '-iname \'*%s*.mkv\' ' % ent.replace('.mkv', '') + \
                      '2> /dev/null'
            if not get_time:
                print('\n'.join(l.strip() for l in run_command(command, do_popen=True)))
            else:
                for line in run_command(command, do_popen=True):
                    cur = line.split()[0]
                    _cmd = run_command(
                        'aviindex -i '
                        '%s -o /dev/null 2> /dev/null' % cur, do_popen=True)
                    timeval = 0
                    for line in _cmd:
                        _line = line.split()
                        if _line[1] == 'V:':
                            nsecs = int(float(_line[5][7:-1]) / float(_line[2]))
                            nmin = int(nsecs / 60.)
                            nhour = int(nmin / 60.)
                            timeval = '%02i:%02i:%02i' % (nhour, nmin % 60, nsecs % 60)
                    if timeval == 0:
                        _cmd = run_command('avconv -i %s 2>&1' % cur, do_popen=True)
                        for line in _cmd:
                            _line = line.split()
                            if _line[0] == 'Duration:':
                                items = _line[1].strip(',').split(':')
                                nhour = int(items[0])
                                nmin = int(items[1])
                                nsecs = int(float(items[2]))
                                timeval = '%02i:%02i:%02i' % (nhour, nmin, nsecs)
                    print('%s %s' % (timeval, cur))
        return 0

    if do_random:
        drama_list = []
        for dir_ in MOVIE_DIRS:
            command = 'find %s/%s -type f ' % (dir_, tv_string) + \
                      '-iname \'*.avi\' 2> /dev/null ; ' + \
                      'find %s/%s -type f ' % (dir_, tv_string) + \
                      '-iname \'*.mp4\' 2> /dev/null ; ' + \
                      'find %s/%s -type f ' % (dir_, tv_string) + \
                      '-iname \'*.mkv\' 2> /dev/null'
            for line in run_command(command, do_popen=True):
                drama_list.append(line.strip())
        if len(drama_list) > 0:
            random.seed(os.urandom(16))
            print(random.sample(drama_list, 1)[0])
        return 0

    run_command(command)

    def read_file(_file):
        """ read file """
        file_size = []
        for line in _file:
            _line = line.split()
            file_size.append([_line[0].split('/')[-1], _line[1], _line[0]])
            if len(_line) > 2:
                file_size.append([_line[2], _line[1], _line[0]])
        return file_size

    disk_file_size = read_file(tmpfile)
    collection_file_size = read_file(open(current_collection, 'r'))
    disk_and_collection = []
    disk_not_collection = []
    disk_not_collection_count = {}

    for i in range(0, len(disk_file_size)):
        is_in_collection = False
        for j in range(0, len(collection_file_size)):
            if disk_file_size[i][0] == collection_file_size[j][0]:
                is_in_collection = True
                disk_and_collection.append(disk_file_size[i][0])
        if is_in_collection is False:
            disk_not_collection.append(disk_file_size[i])
            fname = disk_file_size[i][2].split('/')[-1]
            if fname not in disk_not_collection_count:
                disk_not_collection_count[fname] = 1
            else:
                disk_not_collection_count[fname] += 1

    disk_not_collection.sort()

    total_size = 0
    for _name in disk_not_collection:
        if (not do_television and not no_television) or \
                (do_television and _name[2].find('television') != -1) or \
                (no_television and _name[2].find('television') == -1):
            if tv_string and _name[2].find(tv_string) == -1:
                continue
            fname = _name[2].split('/')[-1]
            if do_uniq and disk_not_collection_count[fname] > 1:
                continue
            size = int(
                run_command('du -s %s' % _name[2], do_popen=True, single_line=True).split()[0])
            total_size += size
            print('%iM %s' % (size / 1024, _name[2]))

    print('%iG' % (total_size / 1024 / 1024))

    if do_dvd:
        _new_collection = open(new_collection, 'a')
        for _name in disk_not_collection:
            _new_collection.write('%s %s\n' % (_name[2], _name[1]))
        _new_collection.close()


def make_list_main():
    """ main function """
    do_dvd_ = False
    do_collection_ = False
    do_television_ = False
    no_television_ = False
    do_uniq_ = False
    do_string_ = False
    do_random_ = False
    get_time_ = False
    do_movies_ = False
    do_disk_ = False
    do_here_ = False
    tv_string_ = 0

    if len(os.sys.argv) > 1:
        if os.sys.argv[1][0] == 'h':
            print('make_list %s' % ', '.join(COMMANDS))
            exit(0)
        if os.sys.argv[1] == '1' or os.sys.argv[1] == 'collection' or \
                os.sys.argv[1] == 'dvd':
            do_dvd_ = True
            if len(os.sys.argv) > 2:
                tv_string_ = os.sys.argv[2]
        if os.sys.argv[1] == '2' or os.sys.argv[1] == 'tv':
            do_television_ = True
            if len(os.sys.argv) > 2:
                tv_string_ = os.sys.argv[2]
        if os.sys.argv[1] == 'uniq_tv':
            do_television_ = True
            do_uniq_ = True
            if len(os.sys.argv) > 2:
                tv_string_ = os.sys.argv[2]
        if os.sys.argv[1] == '3' or os.sys.argv[1] == 'notv':
            no_television_ = True
        if os.sys.argv[1] == 'uniq_notv':
            no_television_ = True
            do_uniq_ = True
        if os.sys.argv[1] == '4' or os.sys.argv[1] == 'list' or \
                os.sys.argv[1] == 'time':
            do_string_ = True
            if os.sys.argv[1] == 'time':
                get_time_ = True
            if len(os.sys.argv) > 2:
                if os.sys.argv[2] == 'here':
                    do_movies_ = True
                    do_here_ = True
                    tv_string_ = sorted(glob.glob('*.avi') + glob.glob('*.mp4'))
                else:
                    tv_string_ = os.sys.argv[2:]
                    if isinstance(tv_string_, str)\
                            or isinstance(tv_string_, unicode):
                        tv_string_ = [tv_string_]
        if os.sys.argv[1] == 'rand':
            do_random_ = True
            if len(os.sys.argv) > 2:
                tv_string_ = os.sys.argv[2]
        if os.sys.argv[1] == '5' or os.sys.argv[1] == 'collection' or \
                os.sys.argv[1] == 'col' or os.sys.argv[1] == 'find':
            do_collection_ = True
            do_string_ = True
            if len(os.sys.argv) > 2:
                tv_string_ = os.sys.argv[2:]
                if isinstance(tv_string_, str)\
                        or isinstance(tv_string_, unicode):
                    tv_string_ = [tv_string_]
        if os.sys.argv[1] == '6' or os.sys.argv[1] == 'mov':
            do_movies_ = True
            if len(os.sys.argv) > 2 and os.sys.argv[2] == 'here':
                do_here_ = True
        if os.sys.argv[1] == '6' or os.sys.argv[1] == 'dsk':
            do_disk_ = True
            if len(os.sys.argv) > 2 and os.sys.argv[2] == 'here':
                do_here_ = True

    with tempfile.NamedTemporaryFile() as tmpfile:
        make_list(
            tmpfile,
            do_dvd=do_dvd_,
            do_collection=do_collection_,
            do_television=do_television_,
            no_television=no_television_,
            do_uniq=do_uniq_,
            do_string=do_string_,
            do_random=do_random_,
            get_time=get_time_,
            do_movies=do_movies_,
            do_disk=do_disk_,
            do_here=do_here_,
            tv_string=tv_string_)
