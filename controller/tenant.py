"""Function to check the tenant to which the Connect account creator belongs."""
import os
from functools import wraps
from google.cloud import firestore
from flask import session, render_template, redirect, Blueprint

db = firestore.Client(project='')
app = Blueprint("tenant", __name__)


def requires_auth(func):
    """Users who are not logged in are redirected to the top page."""
    @wraps(func)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect('/')
        return func(*args, **kwargs)
    return decorated


@app.route('/tenant')
@requires_auth
def tenants():
    """Check the tenant to which you belong."""
    doc_ref = db.collection('tenants').document('')
    doc = doc_ref.get()
    project_list = doc.to_dict()['project_list']
    return render_template(
        'tenants/index.html',
        doc=doc.to_dict(),
        list=list(project_list.keys())
    )
