#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 22:53:33 2016

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import argparse

from movie_collection_app.make_queue import (list_of_commands, help_text,
                                             make_queue)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='make_queue script')
    parser.add_argument('command', nargs='*', help=help_text)
    args = parser.parse_args()

    _command = 'list'
    _args = []

    if hasattr(args, 'command'):
        if len(args.command) > 0:
            _command = args.command[0]
            if _command not in list_of_commands:
                try:
                    _command = int(_command)
                except ValueError:
                    print(help_text)
                    exit(0)
        if len(args.command) > 1:
            for it_ in args.command[1:]:
                try:
                    it_ = int(it_)
                except ValueError:
                    pass
                _args.append(it_)

    out_list = make_queue(_command=_command, _args=_args)
    if len(out_list) > 0:
        print('\n'.join(out_list))
