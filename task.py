import os
import re
import tempfile
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


# Clones the git repo to a temporary directory (so that multiple requests don't produce conflicting git repos)
# Checks out the requested commit. Returns the path to the temporary directory.
def __clone_and_branch_git_repo(commit_id):
    os.chdir(conf.MEI_GIT_SOURCE_DIR)
    tmpdir = tempfile.mkdtemp()

    try:
        output = subprocess.check_output([conf.PATH_TO_GIT_BINARY, 'clone', '.', tmpdir])
    except:
        print('Could not clone git repo to ' + tmpdir)
        return False

    print('Switching repo to git ID ' + commit_id)

    os.chdir(tmpdir)
    try:
        output = subprocess.check_output([conf.PATH_TO_GIT_BINARY, 'checkout', commit_id])
        output = output.decode()
    except subprocess.CalledProcessError:
        print('Could not switch git releases for commit ' + commit_id)
        return False

    return tmpdir


@task(ignore_result=True)
def perform_git_update():
    print("Updating from GitHub")
    os.chdir(conf.MEI_GIT_SOURCE_DIR)
    try:
        output = subprocess.check_output([conf.PATH_TO_GIT_BINARY, 'pull', '--all'])
    except subprocess.CalledProcessError:
        print("An error occurred when updating from GitHub")
        return False

    print('Done git update {0}'.format(output))

    get_binary_git_info.apply_async()
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


@task(ignore_result=True)
def get_binary_git_info():
    import json
    RELNAME = 0
    RELINFO = 1

    os.chdir(conf.MEI_GIT_SOURCE_DIR)
    rel_info = []
    print("Updating from git")

    for rel, rev in conf.RELEASES.items():
        try:
            output = subprocess.check_output([conf.PATH_TO_GIT_BINARY, 'show', '--quiet', rev])
            output = output.decode()
            rel_info.append([rel, output])
        except subprocess.CalledProcessError:
            print("Could not get the latest Git info for commit " + rev)
            return False

    tei_version = None
    with open(os.path.join(conf.PATH_TO_TEI_STYLESHEETS, "VERSION"), 'r') as f:
        tei_version = f.read()
        tei_version = tei_version.strip("\n")

    commit_patt = re.compile(r"commit (?P<rev>[a-f0-9]{40})")
    tstamp_patt = re.compile(r"Date:[\s]+(?P<lcdate>.*)")
    commits = []

    for rel in rel_info:
        commit = ""
        tstamp = ""

        commit_match = re.search(commit_patt, rel[RELINFO])
        if commit_match:
            commit = commit_match.group("rev")

        tstamp_match = re.search(tstamp_patt, rel[RELINFO])
        if tstamp_match:
            tstamp = tstamp_match.group('lcdate')

        commits.append([rel[RELNAME], [commit, tstamp]])

    # write a simple json file to the current directory. The Flask
    # webapp will check this.
    js = dict()
    js['mei_git_revisions'] = commits
    js['tei_stylesheets_version'] = tei_version

    dirn = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dirn, "info.json"), "w") as outfile:
        json.dump(js, outfile)

    return True

@task(track_started=True)
def package_files(output_type, source_file, customization_file, uploaded_source=None, uploaded_customization=None, verbose=False):
    import subprocess
    import tempfile
    import uuid
    import shutil
    import os

    if source_file not in conf.RELEASES.values():
        return {"file": None, "message": "Processing failed. The MEI release specified was not found"}

    current_task.update_state(state='PROGRESS', meta={'process_percent': 25, 'file': None, 'message': None})
    cloned_dir = __clone_and_branch_git_repo(source_file)
    print(cloned_dir)

    tmpdir = tempfile.mkdtemp()
    current_task.update_state(state='PROGRESS', meta={'process_percent': 50, 'file': None, 'message': None})

    transform_bin = None
    output_ext = None
    if output_type == "compiledodd":
        transform_bin = os.path.join(cloned_dir, conf.TEI_TO_COMPILEDODD_BIN)
        output_ext = ".xml"
    elif output_type == "relaxng":
        transform_bin = os.path.join(cloned_dir, conf.TEI_TO_RELAXNG_BIN)
        output_ext = ".rng"
    elif output_type == "documentation":
        transform_bin = os.path.join(cloned_dir, conf.TEI_TO_DOCUMENTATION_BIN)
        output_ext = ".html"

    if uploaded_source:
        local_source = uploaded_source
    else:
        local_source = os.path.join(cloned_dir, conf.MEI_DRIVER_FILE)

    customization = None
    if uploaded_customization and customization_file == "z-local-customization":
        customization = uploaded_customization
    else:
        # This is the path to the customization file in the source checkout
        customization = os.path.join(cloned_dir, conf.AVAILABLE_CUSTOMIZATIONS[customization_file][1])

    # this will name the output file after the customization file, but with the a new extension. whereas the stylesheets will just output
    # a single file.
    docout = ""
    if output_type == "documentation":
        # The canonicalized driver file replaces the customization for the documentation
        customization = os.path.join(tmpdir, 'canonicalized.xml')
        res = subprocess.check_output([conf.PATH_TO_XMLLINT, '--c14n11', local_source, '-o', customization], stderr=subprocess.STDOUT)
        docout = res.decode()

    output_filename = "{0}{1}".format(os.path.splitext(os.path.basename(customization))[0], output_ext)
    tmp_output_path = os.path.join(tmpdir, output_filename)
    cmd = [transform_bin, "--localsource={0}".format(local_source), "{0}".format(customization), tmp_output_path]

    if verbose:
        cmd.insert(1, "--verbose")

    if docout:
        output = docout + '\n'
    else:
        output = ""

    try:
        res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        out = res.decode()
        output += "Transformation Command: {0}\nOutput: {1}\n".format(cmd, out)
    except subprocess.CalledProcessError:
        print("Processing {0} failed. ".format(tmp_output_path))
        print("Command: {0}".format(cmd))
        out = "Processing {0} failed. The command was {1}.".format(tmp_output_path, cmd)
        return {'file': None, 'message': out}

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

    # clean up the cloned directory
    if cloned_dir is not None:
        shutil.rmtree(cloned_dir)

    full_path = os.path.join(full_download_path, output_filename)

    return {'file': full_path, 'message': output}
