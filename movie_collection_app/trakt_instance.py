#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  5 07:43:59 2017

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function, unicode_literals)
import os
import re
import json
from threading import Condition

from trakt import Trakt

from movie_collection_app.movie_collection import MovieCollection
from movie_collection_app.parse_imdb import (
    parse_imdb_mobile_tv, parse_imdb, parse_imdb_episode_list)


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

    def __init__(self, username='ddboline'):
        credentials = read_credentials()
        self.username = username
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.trakt = Trakt.configuration.defaults.client(
            id=self.client_id,
            secret=self.client_secret
        )

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

        print('Enter the code "%s" at %s to authenticate your account' % (
            code.get('user_code'),
            code.get('verification_url')
        ))

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
                x.get_key('imdb'):
                    x for x in Trakt['sync/watchlist'].shows(pagination=True).values()}

    def get_watchlist_seasons(self):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            return Trakt['sync/watchlist'].seasons(pagination=True)

    def get_watchlist_episodes(self):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            return Trakt['sync/watchlist'].episodes(pagination=True)

    def get_watched_shows(self):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            results = {}
            for show in Trakt['sync/watched'].shows(pagination=True).values():
                title = show.title
                imdb_url = show.get_key('imdb')
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
        mq_ = MovieCollection()

        if show in mq_.imdb_ratings:
            return mq_.imdb_ratings[show]
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
        idx = list(mq_.con.execute("select max(index) from imdb_ratings"))
        idx = idx[0][0]
        row_dict = {
            'show': show,
            'title': title,
            'link': imdb_link,
            'rating': rating,
            'istv': type_ == 'tv',
            'index': idx + 1
        }
        mq_.imdb_ratings[show] = row_dict
        keys, vals = zip(*row_dict.items())
        mq_.con.execute("insert into imdb_ratings (%s) values ('%s')" %
                        (', '.join(keys), "', '".join('%s' % x for x in vals)))
        return mq_.imdb_ratings[show]