#!/bin/bash

sudo cp -a ${HOME}/.ssh /root/
sudo chown -R root:root /root/
sudo bash -c "echo deb ssh://ddboline@ddbolineathome.mooo.com/var/www/html/deb/xenial/devel ./ > /etc/apt/sources.list.d/py2deb.list"
sudo apt-get update
sudo apt-get install -y --force-yes python-requests python-dateutil python-psycopg2 python-sqlalchemy \
                                    python-pytest  python-pytest-cov python-numpy=1.\* python-setuptools \
                                    python-dev python-bs4 python-flask
