#!/usr/bin/python
from __future__ import (absolute_import, division, print_function, unicode_literals)
import argparse
import requests
import time
import datetime
import pandas as pd
from bs4 import BeautifulSoup
from dateutil.parser import parse
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

list_of_commands = ('tv', 'season=<>')
help_text = 'commands=%s,[number]' % ','.join(list_of_commands)


def t_request(endpoint):
    timeout = 1
    while True:
        try:
            resp = requests.get(endpoint)
            resp.raise_for_status()
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as exc:
            print('timeout %s, %s' % (timeout, exc))
            time.sleep(timeout)
            timeout *= 2
            if timeout >= 64:
                raise


def get_available_dates_channels(zip_code=10026, tv_prov='NY31534'):
    endpoint = 'http://www.imdb.com/tvgrid'
    # endpoint += '?' + urlencode({'zip': zip_code, 'tv_prov': tv_prov})
    resp = t_request(endpoint)
    if resp.status_code != 200:
        raise Exception('bad status %s' % resp.status_code)
    soup = BeautifulSoup(resp.text, 'html.parser')
    for s in soup.find_all('select'):
        if hasattr(s, 'attrs') and 'name' in s.attrs and s.attrs['name'] == 'start_date':
            available_dates = [o.attrs['value'] for o in s.find_all('option')]
            available_dates = map(lambda x: parse(x).date(), available_dates)
        if hasattr(s, 'attrs') and 'name' in s.attrs and s.attrs['name'] == 'channel':
            available_channels = [
                o.attrs['value'].strip('#') for o in s.find_all('option')
                if '#' in o.attrs['value']]
    return available_dates, available_channels


def get_time_program_list(date=datetime.date.today(), channel='AMC'):
    endpoint = 'http://www.imdb.com/tvgrid/%s/%s' % (str(date), channel)
    resp = t_request(endpoint)
    soup = BeautifulSoup(resp.text, 'html.parser')
    for table in soup.find_all('table'):
        if 'class' not in table.attrs:
            for tr_idx, tr in enumerate(table.find_all('tr')):
                (start_time, start_time_url, title, desc, imdb_title, imdb_url, ep_title,
                 ep_url) = 8 * ['']
                for td_idx, td in enumerate(tr.find_all('td')):
                    if td_idx == 0:
                        start_time = td.text
                        try:
                            start_time_url = [
                                int(a.attrs['href'].split('/')[3]) for a in td.find_all('a')][0]
                        except ValueError:
                            start_time_url = sum(
                                int(x) * 100**i
                                for i, x in enumerate(td.text.split()[0].split(':')[::-1]))
                    else:
                        title = list(td.find_all('b'))[0].text
                        for a in td.find_all('a'):
                            if not imdb_title:
                                imdb_title = a.text
                                imdb_url = a.attrs['href'].split('/')[2]
                            elif not ep_title:
                                ep_title = a.text
                                ep_url = a.attrs['href'].split('/')[2]
                        desc = td.text.replace(title, '').strip()
                        if ep_title:
                            desc = desc.replace(ep_title, '').strip()
                        yield {
                            'start_int': start_time_url,
                            'start_str': start_time,
                            'title': title,
                            'desc': desc,
                            'imdb_title': imdb_title,
                            'imdb_url': imdb_url,
                            'ep_title': ep_title,
                            'ep_url': ep_url}


def get_time_from_grid(date=datetime.date.today(), start_time='0000', channels=None):
    last_date = (
        datetime.datetime.combine(date, datetime.time()) + datetime.timedelta(days=-1)).date()
    resp = t_request('http://www.imdb.com/tvgrid/%s/%s' % (str(date), start_time))
    soup = BeautifulSoup(resp.text, 'html.parser')
    shows = {}
    for div in soup.find_all('div'):
        if 'tv_channel' in div.attrs.get('class', {}):
            channel_name = [
                a.attrs['name'] for x in div.find_all('div')
                if 'tv_callsign' in x.attrs.get('class', {}) for a in x.find_all('a')][0]
            if channels is not None and channel_name not in channels:
                continue

            for li in div.find_all('li'):
                imdb_title, imdb_url = 2 * ['']
                id_ = li.attrs['id'].replace('_show', '_info')
                start_time_ = li.attrs['id'].replace(channel_name, '').replace('_show', '')
                ampm = start_time_[-2:]
                hr = int(start_time_[:-2]) // 100
                mn = int(start_time_[:-2]) % 100
                if start_time == '0000' and ampm == 'PM':
                    start_time_ = parse('%s %02d:%02d %s EST' % (last_date, hr, mn, ampm))
                else:
                    start_time_ = parse('%s %02d:%02d %s EST' % (date, hr, mn, ampm))
                for d in li.find_all('div'):
                    if 'tv_title' not in d.attrs.get('class', {}):
                        continue
                    imdb_title = d.text.strip()
                    for a in d.find_all('a'):
                        imdb_title = a.attrs['title'].strip()
                        imdb_url = a.attrs['href']
                shows[id_] = {
                    'channel': channel_name,
                    'start_time': start_time_,
                    'title': imdb_title,
                    'imdb_title': imdb_title,
                    'imdb_url': imdb_url,
                    'ep_title': '',
                    'ep_url': ''}
        elif 'tv_phantom' in div.attrs.get('class', {}):
            id_ = div.table.attrs.get('id', '')
            if id_ in shows:
                for a in div.find_all('a'):
                    url = a.attrs['href']
                    if shows[id_]['imdb_url'] != url:
                        shows[id_]['ep_url'] = url
                        shows[id_]['ep_title'] = a.text.strip()
    return shows.values()


def parse_imdb_tv_listings():
    available_dates, available_channels = get_available_dates_channels()

    dataframes = []
    for channel in available_channels:
        tmp_dfs = []
        for date in available_dates:
            print('channel %s date %s' % (channel, date))
            last_date = (datetime.datetime.combine(date, datetime.time()) + datetime.timedelta(
                days=-1)).date()
            time_prog_list = list(get_time_program_list(date, channel=channel))
            df = pd.DataFrame(time_prog_list)
            df['start_time'] = df.start_str.apply(lambda x: parse('%s %s EST' % (date, x)))
            if df.shape[0] > 1:
                if df.start_int[0] > df.start_int[1]:
                    df.ix[0, 'start_time'] = parse('%s %s EST' % (last_date, df.start_str[0]))
                df['end_time'] = df.loc[1:, 'start_time'].reset_index(drop=True)
            else:
                df['end_time'] = pd.NaT
            df['channel'] = channel
            tmp_dfs.append(df)
        df = pd.concat(tmp_dfs)
        df = df.sort_values(by=['start_time']).reset_index(drop=True)
        idx = df[df.end_time.isnull()].index
        nidx = idx + 1
        df.loc[df.index.isin(idx[:-1]), 'end_time'] = df[df.index.isin(nidx)].start_time.values
        dataframes.append(df)
    df = pd.concat(dataframes)
    df = df[[
        'channel', 'start_time', 'end_time', 'title', 'imdb_title', 'imdb_url', 'ep_title',
        'ep_url']]

    cc = df.channel.value_counts()

    bad_channels = cc[cc == len(available_dates)].index
    df = df[~df.channel.isin(bad_channels)]
    df2 = get_bad_channels(available_dates, bad_channels)
    df = pd.concat([df, df2]).reset_index(drop=True)
    return df


def get_bad_channels(available_dates, bad_channels):
    dataframes = []
    for date in available_dates:
        for start_time in ['%04d' % (x * 100) for x in range(0, 24, 3)]:
            print(date, start_time)
            time_prog_list = get_time_from_grid(
                date=date, start_time=start_time, channels=bad_channels)
            df_ = pd.DataFrame(time_prog_list)
            dataframes.append(df_)
    df_ = pd.concat(dataframes)
    df_ = df_[['channel', 'start_time', 'title', 'imdb_title', 'imdb_url', 'ep_title',
               'ep_url']].sort_values(by=['channel', 'start_time']).reset_index(drop=True)

    dataframes = []
    for channel in df_.channel.unique():
        tmp_df = df_[df_.channel == channel].reset_index(drop=True)
        if tmp_df.shape[0] > 1:
            tmp_df['end_time'] = tmp_df.loc[1:, 'start_time'].reset_index(drop=True)
        else:
            tmp_df['start_time'] = pd.NaT
        dataframes.append(tmp_df)
    df_ = pd.concat(dataframes)
    return df_[[
        'channel', 'start_time', 'end_time', 'title', 'imdb_title', 'imdb_url', 'ep_title',
        'ep_url']]


def parse_imdb(title='the bachelor'):
    resp = t_request('http://www.imdb.com/find?%s' % urlencode({'s': 'all', 'q': title}))
    if resp.status_code != 200:
        raise Exception('bad status %s' % resp.status_code)
    soup = BeautifulSoup(resp.text, 'html.parser')
    for tr in soup.find_all('tr'):
        for td in tr.find_all('td'):
            if hasattr(td, 'attrs') and 'class' in td.attrs \
                    and 'result_text' in td.attrs['class']:
                title_ = td.text.strip()
                for a in td.find_all('a'):
                    if hasattr(a, 'attrs'):
                        link = a.attrs['href'].split('/')[2]
                        rating_ = parse_imdb_rating(link)
                        yield title_, link, rating_


def parse_imdb_rating(title='tt0313038'):
    resp_ = t_request('http://www.imdb.com/title/%s' % title)
    soup_ = BeautifulSoup(resp_.text, 'html.parser')
    for span in soup_.find_all('span'):
        if 'itemprop' in span.attrs and span.attrs.get('itemprop', None) == 'ratingValue':
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
            title_ = div.text.strip()
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
                        yield (season_, episode, airdate, rating, epi_title, epi_url)


def parse_imdb_argparse():
    from movie_collection_app.movie_collection import MovieCollection

    parser = argparse.ArgumentParser(description='parse_imdb script')
    parser.add_argument('command', nargs='*', help=help_text)
    args = parser.parse_args()

    name = []
    do_tv = False
    do_update = False
    season = None
    if hasattr(args, 'command'):
        for arg in args.command:
            if arg == 'h':
                print(help_text)
            elif arg == 'tv':
                do_tv = True
            elif arg == 'update':
                do_update = True
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
        show_ = ''
        if name.replace(' ', '_') in mc_.imdb_ratings:
            show_ = name.replace(' ', '_')
            title = mc_.imdb_ratings[show_]['title']
            imdb_link = mc_.imdb_ratings[show_]['link']
            rating = mc_.imdb_ratings[show_]['rating']
        else:
            title, imdb_link, rating = parse_imdb_mobile_tv(name)
            for show, val in mc_.imdb_ratings.items():
                if val['link'] == imdb_link:
                    show_ = show
                    break
        print(title, imdb_link, rating)
        if season == -1:
            for item in parse_imdb_episode_list(imdb_link, season=-1):
                season_, _, _, _, _, _ = item
                print(title, season_)
        elif show_:
            if do_update:
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
