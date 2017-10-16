from flask import Flask, url_for, session, jsonify
from flask_oauthlib.client import OAuth
import os

client_id = os.environ['DEX_CLIENT_ID']
client_secret = os.environ['DEX_CLIENT_SECRET']
redirect = '34.215.61.65'

class AppConfig(object):
    DEBUG = True
    SECRET_KEY = 'developer'
    DEXCOM_CLIENT_ID = client_id
    DEXCOM_CLIENT_SECRET = client_secret
    DEXCOM_SCOPE = ['offline_access']

app = Flask(__name__)
app.config.from_object(AppConfig)
# app.config.from_pyfile('dev.cfg', silent=True)

oauth = OAuth(app)

dexcom = oauth.remote_app(
    name='dexcom',
    base_url='https://sandbox-api.dexcom.com',
    access_token_url='https://sandbox-api.dexcom.com/v1/oauth2/token',
    authorize_url='https://sandbox-api.dexcom.com/v1/oauth2/login',
    request_token_params={
        'client_id': client_id,
        'redirect_uri': redirect,
        'response_type': 'code',
        'scope': 'offline_access'
        }
)


@app.route('/')
def home():
    if obtain_dexcom_token():
        response = dexcom.get('v1/oauth2/login')
        return jsonify(response=response.json())
    return '<a href="%s">Login</a>' % url_for('oauth_dexcom')


@app.route('/auth/dexcom')
def oauth_dexcom():
    callback_uri = url_for('oauth_dexcom_callback', _external=True)
    return dexcom.authorize(callback_uri)


@app.route('/auth/dexcom/callback')
def oauth_dexcom_callback():
    response = dexcom.authorized_response()
    if response:
        store_dexcom_token(response)
        return repr(dict(response))
    else:
        return '<a href="%s">T_T Denied</a>' % (url_for('oauth_dexcom'))


@dexcom.tokengetter
def obtain_dexcom_token():
    return session.get('token')


@dexcom.tokensaver
def store_dexcom_token(token):
    session['token'] = token


if __name__ == '__main__':
    app.run()
