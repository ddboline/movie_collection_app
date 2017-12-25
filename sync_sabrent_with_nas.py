#!/usr/bin/python3
from __future__ import (absolute_import, division, print_function, unicode_literals)
import os

from movie_collection_app.sync_sabrent_with_nas import remove_leftover_avi

if __name__ == '__main__':
    dry_run = False
    for arg in os.sys.argv:
        if arg == 'dry_run':
            dry_run = True
    remove_leftover_avi(run_command=(not dry_run))
