from flask import Flask, session, redirect, url_for, request
from flask_oauthlib.client import OAuth
import os

app = Flask(__name__)

oauth = OAuth()

client_id = os.environ['DEX_CLIENT_ID']
client_secret = os.environ['DEX_CLIENT_SECRET']
redirect = '34.215.61.65'

# payload = "client_secret=" + self.client_secret + "&client_id=" + self.client_id + "&code=" + self.authcode + "&grant_type=authorization_code&redirect_uri=" + self.redirect_uri
#
# headers = {
#     'content-type': "application/x-www-form-urlencoded",
#     'cache-control': "no-cache"
#     }

dexcom = oauth.remote_app('dexcom',
    app_key='DEXCOM',
    consumer_key=client_id,
    consumer_secret=client_secret
)

app.config['DEXCOM'] = dict(
    consumer_key=client_id,
    consumer_secret=client_secret,
    base_url='https://sandbox-api.dexcom.com',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://sandbox-api.dexcom.com/v1/oauth2/token',
    authorize_url='https://sandbox-api.dexcom.com/v1/oauth2/login',
    request_token_params={
        'client_id': client_id,
        'redirect_uri': redirect,
        'response_type': 'code',
        'scope': 'offline_access'
        }
)


@dexcom.tokengetter
def get_dexcom_token():
    return session.get('dexcom_token')

@app.route('/login')
def login():
    return dexcom.authorize(callback=url_for('oauth_authorized',
                            _external=True))

@app.route('/osenviron')
def ose():
    return os.environ['DEX_CLIENT_SECRET']

@app.route('/oauth-authorized')
# @dexcom.authorized_handler
def oauth_authorized():
    resp = dexcom.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error'],
            request.args['error_description']
        )
    session['dexcom_token'] = (resp['access_token'], '')
    me = dexcom.get('v2/oauth2/token')
    return jsonify(me.data)

    # next_url = request.args.get('next') or url_for('index')
    # resp = dexcom.authorized_response()
    # if resp is None:
    #     flash(u'You denied the request to sign in.')
    #     return redirect(next_url)
    #
    # session['dexcom_token'] = (
    #     resp['access_token'],
    #     resp['oauth_token_secret']
    # )
    # # session['dexcom_user'] = resp['user_name']
    #
    # flash('You were signed in as %s' % resp['access_token'])
    # return redirect(next_url)

@app.route('/', methods=['GET'])
def index():
    return 'Click here: <a href="https://sandbox-api.dexcom.com/v1/oauth2/login?client_id=eAZxmMneto6aXUbUCVA4h29CT6RKeqvK&redirect_uri=34.215.61.65&response_type=code&scope=offline_access"> link! </a>'


if __name__ == '__main__':
    app.secret_key = client_secret
    oauth.init_app(app)
    app.debug = True
    app.run(host='0.0.0.0', threaded=True)
