#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 20:44:24 2016

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function, unicode_literals)
import os
import re
import datetime
from subprocess import call, Popen, PIPE

HOMEDIR = os.getenv('HOME')
HOSTNAME = os.uname()[1]
REMOTEHOST = 'ddbolineathome.mooo.com'
POSTGRESTRING = 'postgresql://ddboline:BQGIvkKFZPejrKvX@localhost'

dailies = {'the_late_show_with_stephen_colbert', 'the_daily_show', 'the_nightly_show',
           'at_midnight'}


def play_file(fname, yad=False):
    ''' play file using mplayer / mpv '''
    downloaded_file = get_remote_file(fname)
    _cmd = 'mpv --fs --softvol=yes --softvol-max 1000 --vf='
    if yad:
        _cmd = '%syadif,' % _cmd
    _cmd = '%sdsize=470:-2' % _cmd
    if HOSTNAME == 'dilepton2' or HOSTNAME == 'dilepton-tower':
        _cmd = '%s -vo xv' % _cmd
    _cmd = '%s %s' % (_cmd, downloaded_file)
    call(_cmd, shell=True)


def get_length_of_mpg(fname='%s/netflix/mpg/test_roku_0.mpg' % HOMEDIR):
    ''' get length of mpg/avi/mp4 with avconv '''
    if not os.path.exists(fname):
        return -1
    command = 'avconv -i %s 2>&1' % fname
    _cmd = Popen(command, shell=True, stdout=PIPE, close_fds=True).stdout
    nsecs = 0
    for line in _cmd:
        _line = line.split()
        if _line[0] == 'Duration:':
            items = _line[1].strip(',').split(':')
            try:
                nhour = int(items[0])
                nmin = int(items[1])
                nsecs = int(float(items[2])) + nmin * 60 + nhour * 60 * 60
            except ValueError:
                nsecs = -1
    return nsecs


def read_time(fname):
    ''' find duration of mpg/avi/mp4 file using avconv '''
    downloaded_file = has_been_downloaded(fname)
    if not downloaded_file:
        return -1
    return get_length_of_mpg(downloaded_file)


def print_h_m_s(second):
    ''' convert time from seconds to hh:mm:ss format '''
    hours = int(second / 3600)
    minutes = int(second / 60) - hours * 60
    seconds = int(second) - minutes * 60 - hours * 3600
    return '%02i:%02i:%02i' % (hours, minutes, seconds)


def get_remote_file(fname):
    ''' download remote file '''
    if HOSTNAME == 'dilepton-tower':
        return fname
    fn_ = fname.split('/')[-1]
    downloaded_file = '%s/Downloads/%s' % (HOMEDIR, fn_)
    if not os.path.isfile(downloaded_file):
        _command = 'scp ddboline@%s:%s %s' % (REMOTEHOST, fname, downloaded_file)
        call(_command, shell=True)
    return downloaded_file


def get_remote_files(flist):
    ''' download list of files '''
    new_flist = []
    for fname in flist:
        new_flist.append(get_remote_file(fname))
    return new_flist


def has_been_downloaded(fname):
    ''' determine if file has been downloaded '''
    fn_ = fname.split('/')[-1]
    if HOSTNAME == 'dilepton-tower':
        return fname
    downloaded_file = '%s/Downloads/%s' % (HOMEDIR, fn_)
    if not os.path.exists(downloaded_file):
        return False
    return downloaded_file


def remove_remote_file(fname):
    ''' remove local copy of remote file '''
    downloaded_file = '%s/Downloads/%s' % (HOMEDIR, fname.split('/')[-1])
    if HOSTNAME != 'dilepton-tower' and os.path.isfile(downloaded_file):
        _cmd = 'rm %s' % downloaded_file
        call(_cmd, shell=True)


def get_season_episode_from_name(fname, show):
    tmp = fname.split('/')[-1]
    if show not in tmp:
        return -1, -1
    tmp = tmp.split(show)[1]
    if '.' not in tmp:
        return -1, -1
    tmp = tmp.split('.')[0]
    if '_' not in tmp:
        return -1, -1
    tmp = tmp.split('_')
    if len(tmp) < 3:
        return -1, -1
    tmp = tmp[1:3]
    try:
        season = int(tmp[0].strip('s'))
        episode = int(tmp[1].strip('epw'))
        return season, episode
    except Exception:
        return -1, -1


def get_dailies_airdate(fname, show):
    tmp = fname.split('/')[-1]
    if show not in tmp:
        return None
    tmp = tmp.split(show)[1]
    if '.' not in tmp:
        return None
    tmp = tmp.split('.')[0]
    if '_' not in tmp:
        return None
    if len(tmp) < 2:
        return None
    tmp = tmp.strip('_')
    try:
        year = int(tmp[:4])
        month = int(tmp[4:6])
        day = int(tmp[6:8])
        return datetime.date(year=year, month=month, day=day)
    except Exception as exc:
        print(exc, tmp)
        return None


def extract_show(fn_, full_path=True):
    type_ = ''
    if 'television' in fn_ or not full_path:
        if 'unwatched' not in fn_ and full_path:
            show = fn_.split('/')[-3]
            type_ = 'tv'
        else:
            show = fn_.split('/')[-1]
            show = re.sub('_s[0-9]+', ' ', show).split()[0]
            type_ = 'tv'
            for show_ in dailies:
                if show_ in show:
                    show = show_
                    break
    else:
        show = fn_.split('/')[-1].split('.')[0]
        type_ = 'movie'
    return show, type_


class PopenWrapperClass(object):
    """ context wrapper around subprocess.Popen """

    def __init__(self, command):
        """ init fn """
        self.command = command
        self.pop_ = Popen(self.command, shell=True, stdout=PIPE, close_fds=True)

    def __iter__(self):
        return self.pop_.stdout

    def __enter__(self):
        """ enter fn """
        return self.pop_.stdout

    def __exit__(self, exc_type, exc_value, traceback):
        """ exit fn """
        if hasattr(self.pop_, '__exit__'):
            efunc = getattr(self.pop_, '__exit__')
            return efunc(exc_type, exc_value, traceback)
        self.pop_.wait()
        if exc_type or exc_value or traceback:
            return False
        return True


def run_command(command, do_popen=False, turn_on_commands=True, single_line=False):
    ''' wrapper around os.system '''
    if not turn_on_commands:
        print(command)
        return command
    elif do_popen:
        if single_line:
            with PopenWrapperClass(command) as pop_:
                return pop_.read()
        else:
            return PopenWrapperClass(command)
    return call(command, shell=True)


def test_run_command():
    """ test run_command """
    cmd = 'echo "HELLO"'
    out = run_command(cmd, do_popen=True, single_line=True).strip()
    print(out, cmd)
    assert out == b'HELLO'


def walk_wrapper(direc, callback, arg):
    """ wrapper around os.walk for py2/py3 compatibility """
    if hasattr(os.path, 'walk'):
        os.path.walk(direc, callback, arg)
    elif hasattr(os, 'walk'):
        for dirpath, dirnames, filenames in os.walk(direc):
            callback(arg, dirpath, dirnames + filenames)
