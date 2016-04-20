#!/bin/bash

nosetests --with-coverage --cover-package=movie_collection_app ./tests/*.py movie_collection_app/*.py

# pyreverse garmin_app
# for N in classes packages; do dot -Tps ${N}*.dot > ${N}.ps ; ps2pdf ${N}.ps ; done
# ./garmin.py get
# ./garmin.py year run
# ./garmin.py 2014-11-22_18
