#!/usr/bin/python3
from __future__ import (absolute_import, division, print_function, unicode_literals)
from movie_collection_app.trakt_instance import trakt_parse

if __name__ == '__main__':
    try:
        trakt_parse()
    except IOError:
        exit(0)
