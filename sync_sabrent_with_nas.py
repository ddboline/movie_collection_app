#!/usr/bin/python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os

#from movie_collection_app.sync_sabrent_with_nas import sync_sabrent_with_nas
from movie_collection_app.sync_sabrent_with_nas import sync_queue_with_nas


if __name__ == '__main__':
    dry_run = False
    for arg in os.sys.argv:
        if arg == 'dry_run':
            dry_run = True
    sync_queue_with_nas(run_command=(not dry_run))
