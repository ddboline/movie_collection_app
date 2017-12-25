#!/usr/bin/python3
from __future__ import (absolute_import, division, print_function, unicode_literals)
from movie_collection_app.find_new_episodes import find_new_episodes_parse

if __name__ == '__main__':
    try:
        find_new_episodes_parse()
    except IOError:
        exit(0)
