import os
import re
import datetime
import subprocess
import tempfile

import conf

from celery import Celery
from celery.task import task


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return celery.Task.__call__(self, *args, **kwargs)

    celery.Task = ContextTask

    return celery

@task(ignore_result=True)
def perform_svn_update():
    # Update the SVN Repository
    # TODO: Logging needs to be set up for this method.

    os.chdir(conf.MEI_SVN_SOURCE_DIR)
    try:
        output = subprocess.check_output(['svn', 'update'])
    except subprocess.CalledProcessError, e:
        # if, for some reason, the SVN didn't complete, attempt
        # to recover and clean it up.
        output = subprocess.check_output(['svn', 'cleanup'])
        output = subprocess.check_output(['svn', 'update'])
    print("Done svn update")

    os.chdir(os.path.join(conf.MEI_SVN_SOURCE_DIR, "trunk"))
    output = subprocess.check_output(['./build.sh', 'all'])

    files = os.listdir(os.path.join(os.getcwd(), 'build'))
    print(files)

    return True

@task(ignore_result=True)
def package_files(output_type, source_file, customization_file):
    return True