import os
import hmac
import operator
import tempfile

from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import redirect
from flask import url_for
from flask import send_file
from flask import send_from_directory
from flask import make_response

from flask.ext import shelve
from flask_wtf import CsrfProtect

from werkzeug.utils import secure_filename

import conf
from forms import ProcessForm
from task import make_celery
from task import perform_svn_update
from task import package_files

app = Flask(__name__)
app.secret_key = conf.SECRET_KEY
app.config['SHELVE_FILENAME'] = 'customeization.db'
app.config['CELERY_BACKEND'] = 'amqp'
app.config['CELERY_BROKER_URL'] = 'amqp://guest:guest@localhost:5672/'
app.config['LATEST_TAG_2013'] = conf.LATEST_TAG_2013
app.config['LATEST_TAG_2012'] = conf.LATEST_TAG_2012
app.debug = True

shelve.init_app(app)
celery = make_celery(app)

csrf = CsrfProtect()
csrf.init_app(app)

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

        uploaded_customization = None
        # at this point the form will have been checked to make sure the local customization
        # file is present if the local customization option is selected,
        # but we'll do another sanity check here just to make sure.
        if customization_option == 'local-customization' and local_customization is not None:
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

        res = package_files.apply_async(args=[schema_language, source_option, customization_option],
                                        kwargs={"uploaded_customization": uploaded_customization,
                                                "uploaded_source": uploaded_source})

        return redirect(url_for('process_and_download') + "?cid=" + str(res))

    db = shelve.get_shelve('r')
    latest_svn_revision = None
    latest_svn_timestamp = None
    if db.has_key('mei_latest_svn_revision'):
        latest_svn_revision = db['mei_latest_svn_revision']

    if db.has_key('mei_latest_svn_timestamp'):
        latest_svn_timestamp = db['mei_latest_svn_timestamp']

    d = {
        'latest_revision': latest_svn_revision,
        'latest_revision_timestamp': latest_svn_timestamp
    }

    return render_template("index.html", form=form, **d)

@app.route('/process/')
def process_and_download():
    celery_job_id = request.args.get('cid', None)

    db = shelve.get_shelve('r')
    latest_svn_revision = None
    latest_svn_timestamp = None
    if db.has_key('mei_latest_svn_revision'):
        latest_svn_revision = db['mei_latest_svn_revision']

    if db.has_key('mei_latest_svn_timestamp'):
        latest_svn_timestamp = db['mei_latest_svn_timestamp']

    d = {
        'celery_job_id': celery_job_id,
        'latest_revision': latest_svn_revision,
        'latest_revision_timestamp': latest_svn_timestamp
    }

    return render_template("process.html", **d)

@app.route('/progress/')
def progress():
    celery_job_id = request.args.get('cid', None)
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
            'message': None
        }
        # filename = os.path.basename(result['file'])
        # response = send_file(result['file'])
        # response.headers['Content-Disposition'] = 'filename=' + filename
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

@app.route('/google-code/', methods=['POST',])
def googlecode():
    request_body = request.json
    google_code_key = conf.GOOGLE_CODE_AUTHKEY
    m = hmac.new(google_code_key)
    m.update(str(request_body))
    digest = m.hexdigest()

    incoming_header = request.headers.get("HTTP_GOOGLE_CODE_PROJECT_HOSTING_HOOK_HMAC")

    if digest != incoming_header:
        json_resp = jsonify(message="Message Secret was not correct")
        return make_response(json_resp, 400)

    # the revisions may come in a block, but we're only interested in the latest revision.
    revisions = request_body.get('revisions')
    revisions.sort(key=operator.itemgetter('revision'))

    perform_svn_update.apply_async()

    db = shelve.get_shelve('c')
    db['mei_latest_svn_revision'] = revisions[0]['revision']
    db['mei_latest_svn_author'] = revisions[0]['author']
    db['mei_latest_svn_timestamp'] = revisions[0]['timestamp']
    db['mei_latest_svn_url'] = revisions[0]['url']
    # flask-shelve takes care of closing the DB

    json_resp = jsonify(message="Success.")
    return make_response(json_resp, 200)

if __name__ == '__main__':
    app.run()
