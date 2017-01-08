#!/bin/bash

### hack...
export LANG="C.UTF-8"

sudo bash -c "echo deb ssh://ddboline@ddbolineathome.mooo.com/var/www/html/deb/trusty/python3/devel ./ > /etc/apt/sources.list.d/py2deb2.list"
sudo apt-get update
sudo apt-get install -y --force-yes python3-requests python3-pandas python3-dateutil \
                                    python3-psycopg2 python3-sqlalchemy \
                                    python3-pytest python3-pytest-cov python3-numpy=1.\* \
                                    python3-setuptools python3-bs4 python3-flask
