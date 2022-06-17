import os
from functools import wraps
import json
from google.cloud import firestore
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from controller import tenant, custom_form

db = firestore.Client(project='')
app = Flask(__name__)
CORS(app)
app.secret_key = os.environ['app_secret_key']
oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=os.environ['client_id'],
    client_secret=os.environ['client_secret'],
    api_base_url='https://xxx.us.auth0.com',
    access_token_url='https://xxx.us.auth0.com/oauth/token',
    authorize_url='https://xxx.us.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

app.register_blueprint(tenant.app)
app.register_blueprint(custom_form.app)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


@app.route('/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/custom_form')


@app.route('/login')
def login():
    return auth0.authorize_redirect(
        redirect_uri='https://xxx.a.run.app/callback'
    )


@app.route("/")
def home():
    return render_template('home.html')


@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))


@app.route('/logout')
def logout():
    session.clear()
    params = {
        'returnTo': url_for('home', _external=True, _scheme='https',),
        'client_id': os.environ['client_id']
    }
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/api/v1/status')
def api_status():
    return jsonify({'status': 'All green.'})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
