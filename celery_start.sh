#!/usr/bin/env bash

APPDIR=/srv/webapps/customeization
VIRTUALENV=mei_env

source $APPDIR/$VIRTUALENV/bin/activate

exec $APPDIR/$VIRTUALENV/bin/celery -A customeization.celery worker
