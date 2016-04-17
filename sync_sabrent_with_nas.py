#!/usr/bin/python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import glob
import time

from movie_collection_app.util import sync_sabrent_with_nas


if __name__ == '__main__':
    sync_sabrent_with_nas()
