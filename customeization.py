import os
import hmac
import json
from datetime import timedelta
import tempfile

from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import redirect
from flask import url_for
from flask import send_from_directory
from flask import make_response

from flask_wtf import CsrfProtect
from werkzeug.utils import secure_filename

import conf
from forms import ProcessForm
from task import make_celery
from task import perform_svn_update
from task import package_files
from task import get_binary_info

app = Flask(__name__)
app.secret_key = conf.SECRET_KEY

app.config['CELERY_BACKEND'] = 'amqp'
app.config['CELERY_BROKER_URL'] = 'amqp://guest:guest@localhost:5672/'

# Configure the periodic task scheduler.
#  1. 'clean-up-build-directory': Will run once a day to clean up directories in the
#     build directory that are older than a specified time (set in the configuration file, BUILD_EXPIRY)
app.config['CELERYBEAT_SCHEDULE'] = {
    'clean-up-build-directory': {
        'task': 'task.cleanup_build_directory',
        'schedule': timedelta(hours=24)
    }
}
app.config['LATEST_TAG_2013'] = conf.LATEST_TAG_2013
app.config['LATEST_TAG_2012'] = conf.LATEST_TAG_2012
app.debug = True

celery = make_celery(app)
csrf = CsrfProtect()
csrf.init_app(app)

# Check to make sure the app is reporting the latest versions of everything
get_binary_info.apply_async()


@app.route('/', methods=['GET', 'POST'])
def index():
    form = ProcessForm(request.form)

    # If there are form errors it will not pass form.validate() and
    # will fall through to the "GET" handler, passing along the errors
    # to the template.
    # This means we don't have to check the presence of (most) options
    if request.method == 'POST' and form.validate():
        schema_language = request.form.get('schema_language', None)
        source_option = request.form.get('source_options', None)
        canonicalized_source = request.files.get('source_canonical_file', None)
        customization_option = request.form.get('customization_options', None)
        local_customization = request.files.get('local_customization_file', None)
        verbose_output = request.form.get('verbose_output', None)

        uploaded_customization = None
        # at this point the form will have been checked to make sure the local customization
        # file is present if the local customization option is selected,
        # but we'll do another sanity check here just to make sure.
        if customization_option == 'z-local-customization' and local_customization is not None:
            tmpdir = tempfile.mkdtemp()
            filename = secure_filename(local_customization.filename)
            uploaded_customization = os.path.join(tmpdir, filename)
            local_customization.save(uploaded_customization)

        uploaded_source = None
        if source_option == 'local-source' and canonicalized_source is not None:
            tmpdir = tempfile.mkdtemp()
            filename = secure_filename(canonicalized_source.filename)
            uploaded_source = os.path.join(tmpdir, filename)
            canonicalized_source.save(uploaded_source)

        verbose = False
        if verbose_output == "y":
            verbose = True

        res = package_files.apply_async(args=[schema_language, source_option, customization_option],
                                        kwargs={"uploaded_customization": uploaded_customization,
                                                "uploaded_source": uploaded_source,
                                                "verbose": verbose})

        return redirect(url_for('process_and_download') + "?cid=" + str(res))

    latest_svn_revision = None
    latest_svn_timestamp = None
    with open(os.path.join(app.root_path, 'info.json'), 'r') as info:
        js = json.load(info)
        latest_svn_revision = js.get('mei_latest_svn_revision', None)
        latest_svn_timestamp = js.get('mei_latest_svn_timestamp', None)
        tei_stylesheets_version = js.get('tei_stylesheets_version', None)
        tei_roma_version = js.get('tei_roma_version', None)

    d = {
        'latest_revision': latest_svn_revision,
        'latest_revision_timestamp': latest_svn_timestamp,
        'tei_stylesheets_version': tei_stylesheets_version,
        'tei_roma_version': tei_roma_version
    }

    return render_template("index.html", form=form, **d)

@app.route('/process/')
def process_and_download():
    celery_job_id = request.args.get('cid', None)

    # if this is called without a cid, throw the user to the index page.
    if celery_job_id is None:
        return redirect(url_for('index'))

    latest_svn_revision = None
    latest_svn_timestamp = None
    with open(os.path.join(app.root_path, 'svninfo.json'), 'r') as svninfo:
        js = json.load(svninfo)
        latest_svn_revision = js.get('mei_latest_svn_revision', None)
        latest_svn_timestamp = js.get('mei_latest_svn_timestamp', None)

    d = {
        'celery_job_id': celery_job_id,
        'latest_revision': latest_svn_revision,
        'latest_revision_timestamp': latest_svn_timestamp
    }

    return render_template("process.html", **d)

@app.route('/progress/')
def progress():
    celery_job_id = request.args.get('cid', None)

    # if this is called without a cid, throw the user to the index page.
    if celery_job_id is None:
        return redirect(url_for('index'))

    task = celery.AsyncResult(celery_job_id)

    if task.status == 'PROGRESS':
        d = {
            'status': task.status,
            'percentage': 50,
            'download': None,
            'message': None
        }
        return jsonify(d)
    elif task.status == 'SUCCESS':
        result = os.path.relpath(task.result['file'], app.root_path)

        d = {
            'status': task.status,
            'percentage': 100,
            'download': "/" + result,
            'message': task.result['message']
        }
        return jsonify(d)

    elif task.status == 'FAILURE':
        d = {
            'status': task.status,
            'percentage': None,
            'download': None,
            'message': "The task execution failed."
        }
        return jsonify(d), 500
    else:
        d = {
            'status': task.status,
            'percentage': None,
            'download': None,
            'message': None
        }
        return jsonify(d)

@app.route('/build/<path:filename>', methods=['GET'])
def build(filename):
    return send_from_directory(conf.BUILT_SCHEMA_DIR, filename, as_attachment=True)

@csrf.exempt
@app.route('/google-code/', methods=['POST', ])
def googlecode():
    print('Updating from google code.')
    request_body = request.data
    google_code_key = conf.GOOGLE_CODE_AUTHKEY
    m = hmac.new(google_code_key)
    m.update(request_body)
    digest = m.hexdigest()

    incoming_header = request.headers.get("Google-Code-Project-Hosting-Hook-Hmac")

    if digest != incoming_header:
        print("Digest did not match Message Secret")
        json_resp = jsonify(message="Message Secret was not correct")
        return make_response(json_resp, 400)

    # fire this off to Celery to pull in the latest results
    perform_svn_update.apply_async()

    json_resp = jsonify(message="Success.")
    return make_response(json_resp, 200)

if __name__ == '__main__':
    app.run()
