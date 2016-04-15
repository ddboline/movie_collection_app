#!/usr/bin/python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import argparse
import requests
import time
from bs4 import BeautifulSoup
from dateutil.parser import parse
from urllib import urlencode

list_of_commands = ('tv', 'season=<>')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)


def t_request(endpoint):
    timeout = 1
    while True:
        try:
            return requests.get(endpoint)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError) as exc:
            print('timeout %s, %s' % (timeout, exc))
            time.sleep(timeout)
            timeout *= 2
            if timeout >= 64:
                raise


def parse_imdb(title='the bachelor'):
    resp = t_request('http://www.imdb.com/find?%s' % urlencode({'s': 'all',
                                                                'q': title}))
    if resp.status_code != 200:
        raise Exception('bad status %s' % resp.status_code)
    soup = BeautifulSoup(resp.text, 'html.parser')
    for tr in soup.find_all('tr'):
        for td in tr.find_all('td'):
            if hasattr(td, 'attrs') and 'class' in td.attrs \
                    and 'result_text' in td.attrs['class']:
                title_ = td.text.strip().encode(errors='ignore')
                for a in td.find_all('a'):
                    if hasattr(a, 'attrs'):
                        link = a.attrs['href'].split('/')[2]
                        rating_ = parse_imdb_rating(link)
                        yield title_, link, rating_


def parse_imdb_rating(title='tt0313038'):
    resp_ = t_request('http://www.imdb.com/title/%s' % title)
    soup_ = BeautifulSoup(resp_.text, 'html.parser')
    for span in soup_.find_all('span'):
        if 'itemprop' in span.attrs and span.attrs.get(
                'itemprop', None) == 'ratingValue':
            return float(span.text)
    return -1


def parse_imdb_mobile_tv(title='the bachelor'):
    try:
        resp = t_request('http://m.imdb.com/find?%s' % urlencode({'q': title}))
    except requests.exceptions.ConnectionError as exc:
        print(title, exc)
        raise
    if resp.status_code != 200:
        raise Exception('bad status %s' % resp.status_code)
    soup = BeautifulSoup(resp.text, 'html.parser')
    for div in soup.find_all('div'):
        if 'class' in div.attrs and 'title' in div.attrs['class'] \
                and 'TV series' in div.text:
            title_ = div.text.strip().encode(errors='ignore')
            for a in div.find_all('a'):
                if hasattr(a, 'attrs'):
                    link = a.attrs['href'].split('/')[2]
                    try:
                        resp_ = t_request('http://m.imdb.com/title/%s' % link)
                    except requests.exceptions.ConnectionError as exc:
                        print(link, exc)
                        raise
                    soup_ = BeautifulSoup(resp_.text, 'html.parser')
                    for div_ in soup_.find_all('div'):
                        if 'id' in div_.attrs \
                                and div_.attrs['id'] == 'ratings-bar':
                            for span in div_.find_all('span'):
                                if 'class' in span.attrs \
                                        and 'inline-block' \
                                        in span.attrs['class']:
                                    rating_ = span.text.split('/10')[0]
                                    return title_, link, float(rating_)
    return title, '', -1


def parse_imdb_episode_list(imdb_id='tt3230854', season=None):
    try:
        resp = t_request('http://m.imdb.com/title/%s/episodes' % imdb_id)
    except requests.exceptions.ConnectionError as exc:
        print(imdb_id, exc)
        return
    if resp.status_code != 200:
        raise Exception('bad status %s' % resp.status_code)
    soup = BeautifulSoup(resp.text, 'html.parser')
    for a in soup.find_all('a'):
        if hasattr(a, 'attrs') and 'class' in a.attrs \
                and 'season' in a.attrs['class']:
            link = a.attrs['href']
            season_ = int(a.attrs.get('season_number', -1))
            if season == -1 and season_ != -1:
                yield season_, -1, None, -1, 'season', None
                continue
            if season is not None and season != season_:
                continue
            episodes_url = 'http://www.imdb.com/title/%s/episodes/%s' \
                           % (imdb_id, link)
            resp_ = t_request(episodes_url)
            soup_ = BeautifulSoup(resp_.text, 'html.parser')
            for div in soup_.find_all('div'):
                if 'info' in div.attrs.get('class', []) \
                        and div.attrs.get('itemprop', None) == 'episodes':
                    episode, airdate, rating, epi_title = -1, None, -1, None
                    epi_url = None
                    for meta in div.find_all('meta'):
                        if meta.attrs.get('itemprop', None) == 'episodeNumber':
                            episode = meta.attrs.get('content', -1)
                            try:
                                episode = int(episode)
                            except ValueError:
                                pass
                    for div_ in div.find_all('div'):
                        if 'airdate' in div_.attrs.get('class', []) \
                                and div_.text.strip():
                            try:
                                int(div_.text)
                                airdate = None
                            except ValueError:
                                airdate = parse(div_.text).date()
                    for a_ in div.find_all('a'):
                        if epi_url:
                            continue
                        epi_url = a_.attrs.get('href', None)
                        if epi_url:
                            epi_url = epi_url.split('/')
                            if len(epi_url) > 2:
                                epi_url = epi_url[2]
                                epi_title = a_.text.strip()
                                rating = parse_imdb_rating(epi_url)
                            else:
                                print('epi_url', epi_url)
                                epi_url = ''
                    if season_ >= 0 and episode >= 0 and airdate:
                        yield (season_, episode, airdate, rating, epi_title,
                               epi_url)


def parse_imdb_argparse():
    from movie_collection_app.movie_collection import MovieCollection

    parser = argparse.ArgumentParser(description='parse_imdb script')
    parser.add_argument('command', nargs='*', help=help_text)
    args = parser.parse_args()

    name = []
    do_tv = False
    season = None
    if hasattr(args, 'command'):
        for arg in args.command:
            if arg == 'h':
                print(help_text)
            elif arg == 'tv':
                do_tv = True
            elif 'season=' in arg:
                tmp = arg.replace('season=', '')
                try:
                    season = int(tmp)
                except ValueError:
                    pass
                continue
            else:
                name.append(arg.replace('_', ' '))

    name = ' '.join(name)

    mc_ = MovieCollection()

    if do_tv:
        title, imdb_link, rating = parse_imdb_mobile_tv(name)
        show_ = ''
        for show, val in mc_.imdb_ratings.items():
            if val['link'] == imdb_link:
                show_ = show
                break
        print(title, imdb_link, rating)
        if season == -1:
            for item in parse_imdb_episode_list(imdb_link, season=season):
                season_, episode, airdate, ep_rating, ep_title, ep_url = item
                print(title, season_)
        elif show_:
            mc_.get_imdb_episode_ratings(show=show_, season=season)
            mc_.read_imdb_episodes()
            for (season_, episode) in sorted(mc_.imdb_episode_ratings[show_]):
                if season and season != season_:
                    continue
                row = mc_.imdb_episode_ratings[show_][(season_, episode)]
                airdate = row['airdate']
                ep_rating = row['rating']
                ep_title = row['eptitle']
                print(title, season_, episode, airdate, ep_rating, ep_title)
        else:
            for item in parse_imdb_episode_list(imdb_link, season=season):
                season_, episode, airdate, ep_rating, ep_title, ep_url = item
                print(title, season_, episode, airdate, ep_rating, ep_title)
    else:
        for idx, (title, imdb_link, rating) in enumerate(parse_imdb(name)):
            if idx > 2:
                break
            print(idx, title, imdb_link, rating)
