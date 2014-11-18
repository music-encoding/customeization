import os
import re
import datetime
import subprocess
import tempfile

import conf

from celery import Celery, current_task
from celery.task import task


def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_BACKEND'], broker=app.config['CELERY_BROKER_URL'])
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

    # files = os.listdir(os.path.join(os.getcwd(), 'build'))
    return True


@task(track_started=True)
def package_files(output_type, source_file, customization_file):
    import subprocess
    import tempfile
    import os

    tmpdir = tempfile.mkdtemp()

    transform_bin = None
    if output_type == "relaxng":
        transform_bin = conf.TEI_TO_RELAXNG_BIN
        output_ext = ".rng"
    elif output_type == "compiledodd":
        transform_bin = conf.TEI_TO_COMPILEDODD_BIN
        output_ext = ".odd"

    local_source = None
    if source_file == 'schema-2013':
        local_source = conf.MEI_2013_SOURCE_FILE
    elif source_file == 'schema-2012':
        local_source = conf.MEI_2012_SOURCE_FILE
    elif source_file == 'schema-latest':
        local_source = conf.MEI_DEV_SOURCE_FILE

    customization = None
    if customization_file == "meiall-2013":
        customization = conf.MEI_ALL_2013_CUSTOMIZATION
    elif customization_file == "meiall-2012":
        customization = conf.MEI_ALL_2012_CUSTOMIZATION
    elif customization_file == "meiall-develop":
        customization = conf.MEI_ALL_DEV_CUSTOMIZATION

    # this will name the output file after the customization file, but with the a new extension.
    output_filename = "{0}{1}".format(os.path.splitext(os.path.basename(customization))[0], output_ext)
    output_path = os.path.join(tmpdir, output_filename)

    cmd = [transform_bin, "--localsource={0}".format(local_source), "{0}".format(customization), output_path]

    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    for line in proc.stdout:
        print line

    print(output_path)

    for x in range(1):
        process_percent = int(100 * x / 10)
        current_task.update_state(state='PROGRESS', meta={'process_percent': process_percent})

    return True