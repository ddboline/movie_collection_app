#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 10:03:43 2016

@author: ddboline
"""
from __future__ import (absolute_import, division, print_function, unicode_literals)
from traceback import format_exc
from flask import Flask, jsonify
from socket import gethostbyname
from logging import getLogger as get_logger
from subprocess import check_output, call
import urllib

app = Flask(__name__)
log = get_logger()


# straight from flask documentation
class Error(Exception):

    def __init__(self, message, status_code, payload=None):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['msg'] = self.message
        return rv


class BadInputs(Error):

    def __init__(self, message, payload=None):
        Error.__init__(self, message, 400, payload)


@app.errorhandler(BadInputs)
def handle_bad_inputs(error):
    log.error('BAD INPUTS: ' + error.message)
    return jsonify(error.to_dict()), 400


class Internal(Error):

    def __init__(self, message, payload=None):
        Error.__init__(self, message, 500, payload)


@app.errorhandler(Internal)
def handler_internal(error):
    log.error('INTERNAL: ' + error.message)
    return jsonify(error.to_dict()), 500


def _return_tvshows():
    output_str = []
    output = check_output(['/home/ddboline/bin/make_queue', 'tvshows'])
    output_str.append('<center><H3>')
    output_str.append('<table border="0">')
    for line in output.split('\n'):
        if '.avi' in line or '.mp4' in line:
            continue
        show = line.split()
        url = ''
        if show:
            if len(show) > 2 and show[2] != 'None':
                url = show[2]
            show = show[0]
        else:
            continue
        output_str.append('<tr>')
        output_str.append('<td><a href=\"/list/%s\">%s</a></td>' % (show, show))
        output_str.append('<td><a href=\"http://www.imdb.com/title/' '%s\">imdb</a></td>' % url)
        output_str.append('</tr>')
    output_str.append('</table>')
    output_str.append('</H3></center>')
    return output_str


@app.route('/tvshows', methods=['GET'])
def return_tvshows():
    output_str = ['<!DOCTYPE HTML>', '<html>', '<body>']
    output_str.extend(_return_tvshows())
    output_str.append('</body></html>')
    return '\n'.join(output_str), 200


def _return_tvshow(show):
    ipaddr = gethostbyname('dilepton-tower.fios-router.home')
    output_str = [
        """<H3 align="center">
        <button name="remcomout" id="remcomoutput"> &nbsp; </button>
        </H3>"""
    ]
    output_str.append('<center><H3><table border="0">')
    output = check_output(['/home/ddboline/bin/make_queue', 'web', show])
    for line in output.split('\n'):
        show_ = line.split()
        index = -1
        url = ''
        if show_:
            if len(show_) > 2:
                url = show_[2]
            index = show_[0]
            show_ = show_[1]
        else:
            continue
        show_ = show_.split('/')[-1]
        output_str.append('<tr>')
        output_str.append('<td><a href=\"http://'
                          '%s/videos/partial/%s\">%s</a></td>' % (ipaddr, show_, show_))
        if url:
            output_str.append('<td><a href=\"http://www.imdb.com/title/' '%s\">imdb</a></td>' % url)
        output_str.append("""
            <td>
            <button type="submit" id="delete%s" onclick="delete_show('%s');">
            remove </button></td>
                              """ % (index, show_))
        if '.avi' in show_ or '.mkv' in show_:
            output_str.append("""
            <td>
            <button type="submit" id="transode%s" onclick="transcode('%s');">
            transcode </button></td>
                              """ % (index, show_))
    output_str.append('</table></H3></center>')
    output_str.append("""
        <script language="JavaScript" type="text/javascript">
            function transcode(index) {
                var ostr = "../transcode/" + index
                var xmlhttp = new XMLHttpRequest();
                xmlhttp.open("GET", ostr, true);
                xmlhttp.onload = function nothing() {
                }
                xmlhttp.send(null);
                var out = "requested " + index
                document.getElementById("remcomoutput").innerHTML = out;
            }

            function delete_show(index) {
                var ostr = "../delete/" + index
                var xmlhttp = new XMLHttpRequest();
                xmlhttp.open("GET", ostr, true);
                xmlhttp.onload = function nothing() {
                    location.reload();
                }
                xmlhttp.send(null);
            }

            </script>
            """)
    return output_str


@app.route('/list', methods=['GET'], defaults={'show': ''})
@app.route('/list/<show>', methods=['GET'])
def return_tvshow(show):
    try:
        show = urllib.unquote(show)
        output_str = ['<!DOCTYPE HTML>', '<html>', '<body>']
        output_str.append('<H3 align="center">')
        output_str.append('<a href=\"/tvshows\">Go Back</a>')
        output_str.append('</H3>')
        output_str.extend(_return_tvshow(show))
        output_str.append('</body></html>')
        return '\n'.join(output_str), 200
    except Error as e:
        raise e
    except:
        raise Internal(format_exc())

    raise BadInputs('Not sure what happened')


@app.route('/delete/<show>', methods=['GET'])
def request_delete(show):
    try:
        call(['/home/ddboline/bin/make_queue', 'rm', show])
        return '', 200
    except Error as e:
        raise e
    except:
        raise Internal(format_exc())

    raise BadInputs('Not sure what happened')


@app.route('/transcode/<show>', methods=['GET'])
def request_transcode(show):
    try:
        avifile = None
        output = check_output(['/home/ddboline/bin/make_queue', 'list', show])
        for line in output.split('\n'):
            try:
                tmp = line.split()
                if show in tmp[1]:
                    avifile = tmp[1]
                    break
            except IndexError:
                continue
            except ValueError:
                continue
        if avifile:
            call(['/home/ddboline/bin/transcode_avi', avifile, 'add'])
            return '', 200
    except Error as e:
        raise e
    except:
        raise Internal(format_exc())

    raise BadInputs('Not sure what happened')


def run_make_queue_flask():
    app.run(host='0.0.0.0', port=27673)
