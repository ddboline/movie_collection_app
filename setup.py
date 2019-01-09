#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Fri May 22 18:29:26 2015

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function, unicode_literals)
import sys
from setuptools import setup

console_scripts_ = (('find-new-episodes',
                    'movie_collection_app.find_new_episodes:find_new_episodes_parse'),
                   ('trakt-app', 'movie_collection_app.trakt_instance:trakt_parse'))

console_scripts = ['%s = %s' % (x, y) for x, y in console_scripts_]

v = sys.version_info.major
console_scripts.extend('%s%s = %s' % (x, v, y) for x, y in console_scripts_)

setup(
    name='movie_collection_app',
    version='0.0.5.0',
    author='Daniel Boline',
    author_email='ddboline@gmail.com',
    description='movie_collection_app',
    long_description='Movie Collection App',
    license='MIT',
    install_requires=['beautifulsoup4', 'python-dateutil', 'SQLAlchemy', 'psycopg2', 'Flask'],
    packages=['movie_collection_app'],
    package_dir={'movie_collection_app': 'movie_collection_app'},
    # package_data={'sync_app': ['templates/*.html']},
    entry_points={
        'console_scripts': console_scripts
    })
