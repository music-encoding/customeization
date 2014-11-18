import hmac
import operator
from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import make_response

from flask.ext import shelve
from flask_wtf import CsrfProtect

import conf
from forms import ProcessForm
from task import make_celery
from task import perform_svn_update

app = Flask(__name__)
app.secret_key = conf.SECRET_KEY
app.config['SHELVE_FILENAME'] = 'customeization.db'
app.config['CELERY_BROKER_URL'] = 'amqp://guest:guest@localhost:5672/'

shelve.init_app(app)
celery = make_celery(app)

csrf = CsrfProtect()
csrf.init_app(app)

@app.route('/')
def index():
    form = ProcessForm()

    db = shelve.get_shelve('r')
    d = {
        'latest_revision': db['mei_latest_svn_revision'],
        'latest_revision_timestamp': db['mei_latest_svn_timestamp']
    }

    return render_template("index.html", form=form, **d)

@app.route('/process/', methods=['POST'])
def process_and_download():
    print(request.form)
    return render_template("process.html")

@app.route('/progress/')
def progress():
    return jsonify({})


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
    app.debug = True
    app.run()
