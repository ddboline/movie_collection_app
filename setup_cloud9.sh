#!/bin/bash

sudo cp -a ${HOME}/.ssh /root/
sudo chown -R root:root /root/
sudo bash -c "echo deb ssh://ddboline@ddbolineathome.mooo.com/var/www/html/deb/trusty/devel ./ > /etc/apt/sources.list.d/py2deb.list"
sudo apt-get update
sudo apt-get install -y --force-yes python-requests python-dateutil python-psycopg2 python-sqlalchemy \
                                    python-nose  python-coverage python-numpy=1.\* python-setuptools \
                                    python-dev python-bs4 python-flask
