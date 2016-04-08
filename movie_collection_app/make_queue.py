#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 23:00:43 2016

@author: ddboline
"""
import argparse
import os
from subprocess import call

from movie_collection_app.movie_collection import MovieCollection
from movie_collection_app.util import (play_file, remove_remote_file, HOMEDIR,
                                       get_remote_file, get_remote_files,
                                       HOSTNAME)

list_of_commands = ('list', 'get', 'play', 'playyad', 'rm', 'add',
                    'purge', 'time', 'tvshows', 'master', 'slave', 'fifo',
                    'test', 'web', 'addcol')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)


def make_queue(_command='list', _args=None):
    ''' seperate function to run commands from make_queue() '''

    if _command == 'test':
        testfile = '/home/ddboline/public_html/videos/test.mp4'
        play_file(testfile)
        remove_remote_file(testfile)
        testfile = '/home/ddboline/public_html/videos/temp.mp4'
        play_file(testfile)
        remove_remote_file(testfile)
        return []

    mq_ = MovieCollection()
    out_list = []

    if _command == 'list' or _command == 'time' or _command == 'web':
        if not _args:
            out_list += mq_.list_entries(None, do_time=(_command == 'time'))
        elif len(_args) == 1 and _args[0] == 'head':
            out_list += mq_.list_entries(None, first_entry=0, last_entry=20,
                                         do_time=(_command == 'time'))
        elif len(_args) == 1 and _args[0] == 'tail':
            out_list += mq_.list_entries(None, first_entry=-20, last_entry=0,
                                         do_time=(_command == 'time'))
        elif len(_args) == 1 and _args[0] == 'local':
            out_list += mq_.list_entries(None, do_local=True,
                                         do_time=(_command == 'time'))
        elif len(_args) == 1:
            out_list += mq_.list_entries(_args[0],
                                         do_time=(_command == 'time'))
        elif len(_args) == 2 and isinstance(_args[0], int)\
                and isinstance(_args[1], int):
            out_list += mq_.list_entries(None, first_entry=_args[0],
                                         last_entry=_args[1],
                                         do_time=(_command == 'time'))
        elif len(_args) >= 2:
            for arg in _args:
                out_list += mq_.list_entries(arg, do_time=(_command == 'time'))
        if _command == 'web':
            make_web_page_from_string(mq_.list_entries(),
                                      '/tmp/current_queue.html',
                                      do_main_dir=False,
                                      subdir='all')
            if os.path.exists('/tmp/current_queue.html'):
                call('mv /tmp/current_queue.html %s/public_html/videos/'
                     'current_queue.html' % HOMEDIR, shell=True)
            make_web_page_from_string(out_list, do_main_dir=True,
                                      subdir='partial')
    elif _command == 'get':
        if len(_args) == 1 and isinstance(_args[0], int):
            out_list += [get_remote_file(mq_.current_queue[_args[0]])]
        elif len(_args) == 2 and isinstance(_args[0], int)\
                and isinstance(_args[1], int):
            out_list += get_remote_files(mq_.current_queue[_args[0]:_args[1]])
        elif len(_args) >= 1:
            for arg in _args:
                out_list += [mq_.get_entry_by_name(arg)]
    elif _command == 'tvshows':
        if not _args:
            out_list += mq_.list_tvshows()
        elif len(_args) == 1:
            out_list += mq_.list_tvshows(do_random=(_args[0] == 'rand'))
        else:
            out_list += mq_.list_tvshows(do_random=(_args[0] == 'rand'),
                                         play_random=(_args[1] == 'play'))
    elif _command == 'add' and len(_args) > 0:
        for arg in _args:
            if os.path.exists(arg):
                tmp_, _ = mq_.add_entry(arg)
                out_list += tmp_
    elif _command == 'addcol' and len(_args) > 0:
        for arg in _args:
            if os.path.exists(arg):
                tmp_, _ = mq_.add_entry_to_collection(arg)
                out_list += tmp_
    elif _command == 'rm' and len(_args) > 0:
        _args = sorted(_args)
        offset = 0
        if len(_args) == 2 and isinstance(_args[0], int)\
                and isinstance(_args[1], int) and _args[0] < _args[1]\
                and _args[1] < len(mq_.current_queue):
            for idx in range(_args[0], _args[1]+1):
                tm_ = mq_.rm_entry(idx - offset)
                if tm_:
                    out_list += tm_
                    offset += 1
        else:
            for arg in _args:
                if isinstance(arg, int):
                    tm_ = mq_.rm_entry(arg - offset)
                    if tm_:
                        out_list += tm_
                        offset += 1
                else:
                    out_list += mq_.rm_entry_by_name(arg)
                    mq_.read_queue_from_db()
    elif isinstance(_command, int):
        pos = _command
        for arg in _args:
            if isinstance(arg, int):
                continue
            if os.path.exists(arg):
                tmp_, pos_ = mq_.add_entry(arg, position=pos)
                out_list += tmp_
                pos += pos_
    elif _command[0:4] == 'play':
        if len(_args) == 2 and isinstance(_args[0], int)\
                and isinstance(_args[1], int) and _args[0] < _args[1]:
            for idx in range(_args[0], _args[1]):
                play_file(mq_.current_queue[idx], yad=(_command == 'playyad'))
        for arg in _args:
            if isinstance(arg, int) and arg < len(mq_.current_queue):
                print(len(mq_.current_queue))
                play_file(mq_.current_queue[arg]['path'],
                          yad=(_command == 'playyad'))
            else:
                fn_ = mq_.show_entry_by_name(arg)
                if fn_:
                    play_file(fn_, yad=(_command == 'playyad'))
    return out_list


def make_web_page_from_string(in_list=None,
                              queue_file='%s/public_html/videos/' % HOMEDIR +
                                         'video_queue.html',
                              do_main_dir=False, subdir=''):
    ''' write video queue html file '''
    if HOSTNAME != 'dilepton-tower' or not in_list:
        return
    if do_main_dir and os.path.exists('/var/www/html/videos'):
#        os.system('rm -rf %s' % '/'.join(('/var/www/html/videos', subdir)))
        os.system('mkdir -p %s' % '/'.join(('/var/www/html/videos', subdir)))
    with open(queue_file, 'w') as vidfile:
        vidfile.write('<!DOCTYPE HTML>\n')
        vidfile.write('<html>\n')
        vidfile.write('<body>\n')
        vidfname = ''
        for line in in_list:
            idx = -1
            cur = ''
            ents = line.split()
            idx = int(ents[0])
            cur = ents[1]
            if 'sabrent2000' in cur:
                vidfname = cur.replace('/media/sabrent2000/Documents/movies',
                                       'movies')\
                              .replace(
                                  '/media/sabrent2000/television/unwatched',
                                  'television')
            if 'caviar2000' in cur:
                vidfname = cur.replace('/media/caviar2000/Documents/movies',
                                       'movies2')
            if 'western2000' in cur:
                vidfname = cur.replace('/media/western2000/Documents/movies',
                                       'movies3')
            if do_main_dir and os.path.exists('/'.join(('/var/www/html/videos',
                                                        subdir))):
                link_path = '%s/%s' % (
                    '/'.join(('/var/www/html/videos', subdir)),
                    os.path.basename(cur))
                if not os.path.exists(link_path):
                    os.system('rm -rf %s' % link_path)
                    os.system('ln -s %s %s' % (cur, link_path))
                vidfname = '../videos/%s' % os.path.basename(cur)
            vidname = cur.split('/')[-1].replace('_', ' ')
            vidfile.write('<H3 align="center">\n<a href="../%s">' % vidfname +
                          '%03i\t%s</a>\n</H3>\n\n' % (idx, vidname))
        vidfile.write('</body>\n')
        vidfile.write('</html>\n')


def make_queue_parse():
    parser = argparse.ArgumentParser(description='make_queue script')
    parser.add_argument('command', nargs='*', help=help_text)
    args = parser.parse_args()

    _command = 'list'
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

    out_list = make_queue(_command=_command, _args=_args)
    if len(out_list) > 0:
        out_list = '\n'.join(out_list)
        try:
            print(out_list)
        except IOError:
            pass
