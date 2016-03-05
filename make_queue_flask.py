#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 23 10:11:53 2016

@author: ddboline

flask app for make_queue
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from movie_collection_app.movie_queue_flask import run_make_queue_flask


if __name__ == '__main__':
    run_make_queue_flask()
