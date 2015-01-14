#!/usr/bin/env bash

APPDIR=/srv/webapps/customeization
VIRTUALENV=mei_env

source $APPDIR/$VIRTUALENV/bin/activate

exec uwsgi --ini $APPDIR/customeization_uwsgi.ini