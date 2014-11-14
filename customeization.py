import hmac
import operator
from flask import Flask
from flask import render_template
from flask import request
from flask import Response
from flask.ext import shelve

import conf
from task import make_celery
from task import perform_svn_update

app = Flask(__name__)
app.config['SHELVE_FILENAME'] = 'customeization.db'
app.config['CELERY_BROKER_URL'] = 'amqp://guest:guest@localhost:5672/'

shelve.init_app(app)
celery = make_celery(app)


@app.route('/')
def index():
    db = shelve.get_shelve('r')
    print db['mei_latest_svn_revision']

    return render_template("base.html")


@app.route('/google-code', methods=['POST',])
def googlecode():
    request_body = request.json
    google_code_key = conf.GOOGLE_CODE_AUTHKEY
    m = hmac.new(google_code_key)
    m.update(str(request_body))
    digest = m.hexdigest()

    incoming_header = request.headers.get("HTTP_GOOGLE_CODE_PROJECT_HOSTING_HOOK_HMAC")

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

    return Response()

if __name__ == '__main__':
    app.debug = True
    app.run()
