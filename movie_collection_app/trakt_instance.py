#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  5 07:43:59 2017

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function, unicode_literals)
import os
import json
from threading import Condition
import argparse

from trakt import Trakt

from movie_collection_app.movie_collection import MovieCollection
from movie_collection_app.parse_imdb import parse_imdb_mobile_tv, parse_imdb

list_of_commands = ('list', 'search', 'add', 'cal', 'rm')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)


def read_credentials():
    credentials = {}
    with open('%s/.trakt/credentials' % os.getenv('HOME')) as f:
        for line in f:
            tmp = line.split('=')
            if len(tmp) > 1:
                key, val = [x.strip() for x in tmp][:2]
                credentials[key] = val
    return credentials


class TraktInstance(object):
    auth_token = '%s/.trakt/auth_token.json' % os.getenv('HOME')

    def __init__(self, username='ddboline', mq_=None):
        credentials = read_credentials()
        self.username = username
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.trakt = Trakt.configuration.defaults.client(
            id=self.client_id, secret=self.client_secret)

        if mq_ is not None:
            self.mq_ = mq_
        else:
            self.mq_ = MovieCollection()

        self.is_authenticating = Condition()

        self.authorization = None

        # Bind trakt events
        Trakt.on('oauth.token_refreshed', self.on_token_refreshed)

        self.read_auth()

        if self.authorization is None:
            self.authenticate()

    def authenticate(self):
        if not self.is_authenticating.acquire(blocking=False):
            print('Authentication has already been started')
            return False

        # Request new device code
        code = Trakt['oauth/device'].code()

        print('Enter the code "%s" at %s to authenticate your account' %
              (code.get('user_code'), code.get('verification_url')))

        # Construct device authentication poller
        poller = Trakt['oauth/device'].poll(**code)\
            .on('aborted', self.on_aborted)\
            .on('authenticated', self.on_authenticated)\
            .on('expired', self.on_expired)\
            .on('poll', self.on_poll)

        # Start polling for authentication token
        poller.start(daemon=False)

        # Wait for authentication to complete
        return self.is_authenticating.wait()

    def run(self):

        if not self.authorization:
            print('ERROR: Authentication required')
            exit(1)
        else:
            print('authorization:', self.authorization)

        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            # Expired token will be refreshed automatically (as `refresh=True`)
            print(Trakt['sync/watchlist'].shows(pagination=True))

    def get_watchlist_shows(self):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            return {
                x.get_key('imdb'): x
                for x in Trakt['sync/watchlist'].shows(pagination=True).values()
            }

    def get_watchlist_seasons(self):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            return Trakt['sync/watchlist'].seasons(pagination=True)

    def get_watchlist_episodes(self):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            return Trakt['sync/watchlist'].episodes(pagination=True)

    def get_watched_shows(self, imdb_id=None):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            results = {}
            for show in Trakt['sync/watched'].shows(pagination=True).values():
                title = show.title
                imdb_url = show.get_key('imdb')
                if imdb_id is not None and imdb_url != imdb_id:
                    continue
                episodes = {}
                for (season, epi), episode in show.episodes():
                    episodes[(season, epi)] = {
                        'title': title,
                        'imdb_url': imdb_url,
                        'season': season,
                        'episode': epi
                    }
                results[imdb_url] = episodes
            return results

    def on_aborted(self):
        """Device authentication aborted.

        Triggered when device authentication was aborted (either with `DeviceOAuthPoller.stop()`
        or via the "poll" event)
        """

        print('Authentication aborted')

        # Authentication aborted
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_authenticated(self, authorization):
        """Device authenticated.

        :param authorization: Authentication token details
        :type authorization: dict
        """

        # Acquire condition
        self.is_authenticating.acquire()

        # Store authorization for future calls
        self.authorization = authorization

        print('Authentication successful - authorization: %r' % self.authorization)

        # Authentication complete
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_expired(self):
        """Device authentication expired."""

        print('Authentication expired')

        # Authentication expired
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_poll(self, callback):
        """Device authentication poll.

        :param callback: Call with `True` to continue polling, or `False` to abort polling
        :type callback: func
        """

        # Continue polling
        callback(True)

    def on_token_refreshed(self, authorization):
        # OAuth token refreshed, store authorization for future calls
        self.authorization = authorization

        print('Token refreshed - authorization: %r' % self.authorization)

    def store_auth(self):
        with open(self.auth_token, 'w') as f:
            json.dump(self.authorization, f)

    def read_auth(self):
        if not os.path.exists(self.auth_token):
            self.authorization = None
        with open(self.auth_token, 'r') as f:
            self.authorization = json.load(f)

    def get_imdb_rating(self, show, imdb_url, type_='tv'):

        if show in self.mq_.imdb_ratings:
            return self.mq_.imdb_ratings[show]
        show_ = show.replace('_', ' ')
        title = None
        if type_ == 'tv':
            title, imdb_link, rating = parse_imdb_mobile_tv(show_)
        else:
            for title, imdb_link, rating in parse_imdb(show_):
                if 'TV Series' not in title and 'TV Mini-Series' not in title:
                    break
        if imdb_link != imdb_url:
            raise Exception('Bad imdb link %s' % imdb_link)
        if title is None:
            return {
                'show': show,
                'title': title,
                'link': None,
                'rating': -1,
                'istv': False,
                'index': -1
            }
        title = title.replace("'", '')
        print(show, title, imdb_link, rating)
        idx = list(self.mq_.con.execute("select max(index) from imdb_ratings"))
        idx = idx[0][0]
        row_dict = {
            'show': show,
            'title': title,
            'link': imdb_link,
            'rating': rating,
            'istv': type_ == 'tv',
            'index': idx + 1
        }
        self.mq_.imdb_ratings[show] = row_dict
        keys, vals = zip(*row_dict.items())
        self.mq_.con.execute("insert into imdb_ratings (%s) values ('%s')" %
                             (', '.join(keys), "', '".join('%s' % x for x in vals)))
        return self.mq_.imdb_ratings[show]

    def do_lookup(self, imdb_id):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            return Trakt['search'].lookup(id=imdb_id, service='imdb')

    def do_query(self, show, media='show'):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            if show in self.mq_.imdb_ratings:
                imdb = self.mq_.imdb_ratings[show]['link']
                show = self.do_lookup(imdb_id=imdb)
                return {imdb: show}
            else:
                shows = Trakt['search'].query(show.replace('_', ' '), media=media, pagination=True)
                shows = {s.get_key('imdb'): s for s in shows}
                return shows

    def add_show_to_watchlist(self, show=None, imdb_id=None):
        if imdb_id:
            show_obj = self.do_lookup(imdb_id)
        elif show:
            show_obj = self.do_query(show)
        if isinstance(show_obj, list):
            if len(show_obj) < 1:
                return
            else:
                show_obj = show_obj[0]
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            items = {'shows': [show_obj.to_dict()]}
            print(show_obj)
            return Trakt['sync/watchlist'].add(items=items)

    def add_episode_to_watched(self, show=None, imdb_id=None, season=None, episode=None):
        if imdb_id:
            show_obj = self.do_lookup(imdb_id)
        elif show:
            show_obj = self.do_query(show)
        if isinstance(show_obj, list):
            if len(show_obj) < 1:
                return
            else:
                show_obj = show_obj[0]
        if season and episode:
            episode_ = Trakt['shows'].episode(
                show_obj.get_key('imdb'), season=season, episode=episode)
            if not episode_:
                return False
            with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
                items = {'episodes': [episode_.to_dict()]}
                print(episode_)
                return Trakt['sync/history'].add(items=items)
        elif season:
            with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
                episodes = Trakt['shows'].season(show_obj.get_key('imdb'), season=season)
                if not episodes:
                    return False
                episodes = [e.to_dict() for e in episodes]
                items = {'episodes': episodes}
                print(episodes)
                return Trakt['sync/history'].add(items=items)

    def remove_show_to_watchlist(self, show=None, imdb_id=None):
        if imdb_id:
            show_obj = self.do_lookup(imdb_id)
        elif show:
            show_obj = self.do_query(show)
        if isinstance(show_obj, list):
            if len(show_obj) < 1:
                return
            else:
                show_obj = show_obj[0]
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            items = {'shows': [show_obj.to_dict()]}
            print(show_obj)
            return Trakt['sync/watchlist'].remove(items=items)

    def remove_episode_to_watched(self, show=None, imdb_id=None, season=None, episode=None):
        if imdb_id:
            show_obj = self.do_lookup(imdb_id)
        elif show:
            show_obj = self.do_query(show)
        if isinstance(show_obj, list):
            if len(show_obj) < 1:
                return
            else:
                show_obj = show_obj[0]
        if season and episode:
            episode_ = Trakt['shows'].episode(
                show_obj.get_key('imdb'), season=season, episode=episode)
            with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
                items = {'episodes': [episode_.to_dict()]}
                print(episode_)
                return Trakt['sync/history'].remove(items=items)
        elif season:
            with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
                episodes = []
                for episode_ in Trakt['shows'].season(show_obj.get_key('imdb'), season=season):
                    episodes.append(episode_.to_dict())
                items = {'episodes': episodes}
                print(episodes)
                return Trakt['sync/history'].remove(items=items)

    def get_calendar(self):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            result = Trakt['calendars/my/*'].get(media='shows', pagination=True)
            return result


def trakt_parse():
    parser = argparse.ArgumentParser(description='find_new_episodes script')
    parser.add_argument('command', nargs='*', help=help_text)
    args = parser.parse_args()

    _command = 'list'
    _args = []

    if hasattr(args, 'command'):
        for arg in args.command:
            if arg in list_of_commands:
                _command = arg
            else:
                _args.append(arg)

    ti_ = TraktInstance()

    if _command == 'list':
        if len(_args) == 0 or _args[0] == 'watchlist':
            print('\n'.join('%s : %s' % (k, v) for k, v in ti_.get_watchlist_shows().items()))
        elif _args[0] == 'watched':
            if len(_args) > 1:
                imdb = _args[1]
                if imdb in ti_.mq_.imdb_ratings:
                    imdb = ti_.mq_.imdb_ratings[imdb]['link']
                if len(_args) > 2:
                    print('\n'.join('%s : %s' % (
                        k, v) for k, v in sorted(ti_.get_watched_shows(imdb_id=imdb)[imdb].items())
                                    if v['season'] == int(_args[2])))
                else:
                    print('\n'.join(
                        '%s : %s' % (k, v)
                        for k, v in sorted(ti_.get_watched_shows(imdb_id=imdb).get(imdb, {}).items())))
            else:
                print('\n'.join('%s : %s %s' % (k, [x['title'] for x in v.values()][0], len(v))
                                for k, v in ti_.get_watched_shows().items()))
    elif _command == 'search':
        print('\n'.join(['%s %s' % (k, v) for k, v in ti_.do_query(_args[0]).items()]))
    elif _command == 'add':
        imdb = _args[1]
        if imdb in ti_.mq_.imdb_ratings:
            imdb = ti_.mq_.imdb_ratings[imdb]['link']
        if _args[0] == 'watched':
            season, episode = _args[2], None
            if len(_args) > 3:
                episode = _args[3]
            print(ti_.do_lookup(imdb_id=imdb), season, episode)
            print(ti_.add_episode_to_watched(imdb_id=imdb, season=season, episode=episode))
        elif _args[0] == 'watchlist':
            print(ti_.add_show_to_watchlist(imdb_id=imdb))
    elif _command == 'rm':
        imdb = _args[1]
        if imdb in ti_.mq_.imdb_ratings:
            imdb = ti_.mq_.imdb_ratings[imdb]['link']
        if _args[0] == 'watched':
            season, episode = _args[2], None
            if len(_args) > 3:
                episode = _args[3]
            print(ti_.do_lookup(imdb_id=imdb), season, episode)
            print(ti_.remove_episode_to_watched(imdb_id=imdb, season=season, episode=episode))
        elif _args[0] == 'watchlist':
            print(ti_.remove_show_to_watchlist(imdb_id=imdb))
    elif _command == 'cal':
        print('\n'.join([
            '%s %s %s' % (x.show.title, x.pk, x.first_aired.date().isoformat())
            for x in ti_.get_calendar()
        ]))
