import os
import re
import subprocess
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

    # update the SVN info JSON file
    parse_svn_info.apply_async()

    return True

# Cleans up the `build` directory after a set period of time. This
# is registered as an automatic celery task (not called explicitly).
@task(ignore_result=True)
def cleanup_build_directory():
    import datetime
    import shutil

    print("Checking build directory for cleanup")

    tnow = datetime.datetime.now()
    for d in os.listdir(conf.BUILT_SCHEMA_DIR):
        ctime = os.path.getctime(os.path.join(conf.BUILT_SCHEMA_DIR, d))
        ctime_tstamp = datetime.datetime.fromtimestamp(ctime)
        delta = tnow - ctime_tstamp
        if delta > datetime.timedelta(hours=conf.BUILD_EXPIRY):
            print("Removing: {0}".format(d))
            shutil.rmtree(os.path.join(conf.BUILT_SCHEMA_DIR, d))

# Parses the result of `svn info` and updates the svninfo.json
# file with the result so that it can be displayed on the pages.
@task(ignore_result=True)
def parse_svn_info():
    import json
    os.chdir(conf.MEI_SVN_SOURCE_DIR)

    output = None
    try:
        output = subprocess.check_output(['svn', 'info'])
    except subprocess.CalledProcessError, e:
        output = subprocess.check_output(['svn', 'cleanup'])
        output = subprocess.check_output(['svn', 'info'])
    print("Done svn info lookup")

    if output:
        rev_patt = re.compile(r"Revision: (?P<rev>[0-9]+)")
        tstamp_patt = re.compile(r"Last Changed Date: .* \((?P<lcdate>.*)\)")
        revision = ""
        tstamp = ""

        rev_match = re.search(rev_patt, output)
        if rev_match:
            revision = rev_match.group('rev')

        tstamp_match = re.search(tstamp_patt, output)
        if tstamp_match:
            tstamp = tstamp_match.group('lcdate')

        # write a simple json file to the current directory. The Flask
        # webapp will check this.
        js = dict()
        js['mei_latest_svn_revision'] = revision
        js['mei_latest_svn_timestamp'] = tstamp

        dirn = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dirn, "svninfo.json"), "w") as outfile:
            json.dump(js, outfile)

    return True

@task(track_started=True)
def package_files(output_type, source_file, customization_file, uploaded_source=None, uploaded_customization=None):
    import subprocess
    import tempfile
    import uuid
    import shutil
    import os

    tmpdir = tempfile.mkdtemp()
    current_task.update_state(state='PROGRESS', meta={'process_percent': 50, 'file': None, 'message': None})

    transform_bin = None
    output_ext = None
    if output_type == "compiledodd":
        transform_bin = conf.TEI_TO_COMPILEDODD_BIN
        output_ext = ".xml"
    else:  # relaxng
        transform_bin = conf.TEI_TO_RELAXNG_BIN
        output_ext = ".rng"

    local_source = None
    if source_file == 'schema-2013':
        local_source = conf.MEI_2013_SOURCE_FILE
    elif source_file == 'schema-2012':
        local_source = conf.MEI_2012_SOURCE_FILE
    elif source_file == 'schema-latest':
        local_source = conf.MEI_DEV_SOURCE_FILE
    elif source_file == 'local-source':
        local_source = uploaded_source

    customization = None
    if customization_file == "meiall-2013":
        customization = conf.MEI_ALL_2013_CUSTOMIZATION
    elif customization_file == "meiall-2012":
        customization = conf.MEI_ALL_2012_CUSTOMIZATION
    elif customization_file == "meiall-develop":
        customization = conf.MEI_ALL_DEV_CUSTOMIZATION
    elif customization_file == 'local-customization':
        customization = uploaded_customization

    # this will name the output file after the customization file, but with the a new extension.
    output_filename = "{0}{1}".format(os.path.splitext(os.path.basename(customization))[0], output_ext)

    tmp_output_path = os.path.join(tmpdir, output_filename)
    cmd = [transform_bin, "--localsource={0}".format(local_source), "{0}".format(customization), tmp_output_path]

    output = None
    try:
        output = subprocess.check_output(cmd)
        print(output)
    except subprocess.CalledProcessError, e:
        print("Processing {0} failed. ".format(tmp_output_path))
        print("Command: {0}".format(cmd))
        return False

    # downloads will be stored in a UUID directory name to avoid filename clashes.
    tmp_download_dir = str(uuid.uuid4())
    full_download_path = os.path.join(conf.BUILT_SCHEMA_DIR, tmp_download_dir)

    os.mkdir(full_download_path)

    # move the file from the temporary directory to the download directory
    shutil.move(tmp_output_path, full_download_path)

    # clean up the temporary directory
    shutil.rmtree(tmpdir)

    # clean up any other files the user may have uploaded
    if uploaded_source is not None:
        shutil.rmtree(os.path.dirname(uploaded_source))

    if uploaded_customization is not None:
        shutil.rmtree(os.path.dirname(uploaded_customization))

    full_path = os.path.join(full_download_path, output_filename)

    return {'file': full_path}