from functools import wraps
from google.cloud import firestore
from flask import Flask, request, send_file, abort, Blueprint
from flask import redirect
from flask import render_template
from flask import session

db = firestore.Client(project='')
app = Blueprint("tenant", __name__)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


@app.route('/tenant')
@requires_auth
def tenants():
    doc_ref = db.collection(u'tenants').document('')
    doc = doc_ref.get()
    project_list = doc.to_dict()['project_list']

    return render_template(
        'tenants/index.html',
        doc=doc.to_dict(),
        list=list(project_list.keys())
    )