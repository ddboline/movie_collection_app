#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 20:44:24 2016

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os

nasbase = '/media/dileptonnas/Documents'
sabbase = '/media/sabrent2000/Documents'
nasbase = sabbase


def remove_leftover_avi(run_command=False):
    naspaths = ('%s/television' % nasbase,
                '%s/movies' % nasbase)
    for naspath in naspaths:
        for root, dirs, files in os.walk(naspath):
            for fn_ in files:
                if '.mp4' not in fn_:
                    continue
                fname = '%s/%s' % (root, fn_)
                fname_avi = fname.replace('.mp4', '.avi')
                fname_mkv = fname.replace('.mp4', '.mkv')

                if os.path.exists(fname_avi):
                    print(fname_avi)
                    if run_command:
                        os.remove(fname_avi)
                if os.path.exists(fname_mkv):
                    print(fname_mkv)
                    if run_command:
                        os.remove(fname_mkv)
