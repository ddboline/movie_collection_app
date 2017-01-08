#!/bin/bash

sudo cp -a ${HOME}/.ssh /root/
sudo chown -R root:root /root/
sudo bash -c "echo deb ssh://ddboline@ddbolineathome.mooo.com/var/www/html/deb/trusty/devel ./ > /etc/apt/sources.list.d/py2deb2.list"
sudo apt-get update
sudo /opt/conda/bin/conda install -c https://conda.anaconda.org/ddboline --yes requests \
        python-dateutil psycopg2 sqlalchemy pytest pytest-cov beautifulsoup4 flask
