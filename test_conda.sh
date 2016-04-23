#!/bin/bash

nosetests --with-coverage --cover-package=movie_collection_app ./tests/*.py movie_collection_app/*.py

# rm -rf ${HOME}/run/
# python3 ./garmin.py get
# python3 ./garmin.py year run
# python3 ./garmin.py 2014-11-22_18
