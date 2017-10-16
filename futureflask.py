from flask import Flask, session, redirect, url_for, request
from flask_oauthlib.client import OAuth
import os

app = Flask(__name__)
oauth = OAuth()

client_id = os.environ['DEX_CLIENT_ID']
client_secret = os.environ['DEX_CLIENT_SECRET']
redirect_uri = '34.215.61.65'

dexcom = oauth.remote_app('dexcom',
    base_url='https://sandbox-api.dexcom.com',
    request_token_url=None,
    access_token_url='https://sandbox-api.dexcom.com/v1/oauth2/token',
    authorize_url='https://sandbox-api.dexcom.com/v1/oauth2/login',
    consumer_key=client_id,
    consumer_secret=client_secret
)

@dexcom.tokengetter
def get_dexcom_token(token=None):
    return session.get('dexcom_token')

@app.route('/login')
def login():
    return dexcom.authorize(callback=url_for('oauth_authorized',
                next=request.args.get('next') or request.referrer
                or None, _external=True))

@app.route('/osenviron')
def ose():
    return os.environ['DEX_CLIENT_ID']

@app.route('/oauth-authorized')
# @dexcom.authorized_response()
def oauth_authorized():
    next_url = request.args.get('next') or url_for('index')
    resp = dexcom.authorized_response()
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)

    session['dexcom_token'] = (
        resp['oauth_token'],
        resp['oauth_token_secret']
    )
    session['dexcom_user'] = resp['user_name']

    flash('You were signed in as %s' % resp['screen_name'])
    return redirect(next_url)

@app.route('/', methods=['GET'])
def index():
    return 'Click here: <a href="https://sandbox-api.dexcom.com/v1/oauth2/login?client_id=eAZxmMneto6aXUbUCVA4h29CT6RKeqvK&redirect_uri=34.215.61.65&response_type=code&scope=offline_access"> link! </a>'


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
