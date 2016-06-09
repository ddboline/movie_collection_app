#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Fri May 22 18:29:26 2015

@author: ddboline
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

from setuptools import setup

console_scripts = (
    ('make-queue', 'movie_collection_app.make_queue:make_queue_parse'),
    ('parse-imdb', 'movie_collection_app.parse_imdb:parse_imdb_argparse'),
    ('movie-queue-flask', 'movie_collection_app.movie_queue_flask:'
     'run_make_queue_flask'),
    ('make-collection', 'movie_collection_app.make_collection:'
     'make_collection_parse'),
    ('make-list', 'movie_collection_app.make_list:make_list_main'),
    ('find-new-episodes', 'movie_collection_app.find_new_episodes:'
     'find_new_episodes_parse'))
console_scripts = ['%s = %s' % (x[0], x[1]) for x in console_scripts]

setup(
    name='movie_collection_app',
    version='0.0.1.1',
    author='Daniel Boline',
    author_email='ddboline@gmail.com',
    description='movie_collection_app',
    long_description='Movie Collection App',
    license='MIT',
    install_requires=['beautifulsoup4', 'python-dateutil', 'SQLAlchemy',
                      'psycopg2', 'Flask'],
    packages=['movie_collection_app'],
    package_dir={'movie_collection_app': 'movie_collection_app'},
    #package_data={'sync_app': ['templates/*.html']},
    entry_points={'console_scripts': console_scripts}
)
