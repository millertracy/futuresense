# from flask import Flask, url_for, session, jsonify
# from flask_oauthlib.client import OAuth
# import os
#
# client_id = os.environ['DEX_CLIENT_ID']
# client_secret = os.environ['DEX_CLIENT_SECRET']
# redirect = '34.215.61.65'
#
# app = Flask(__name__)
#
# oauth = OAuth(app)
#
# dexcom = oauth.remote_app('dexcom',
#     app_key='DEXCOM',
#     consumer_key=client_id,
#     consumer_secret=client_secret
# )
#
# app.config['DEXCOM'] = dict(
#     consumer_key=client_id,
#     consumer_secret=client_secret,
#     base_url='https://sandbox-api.dexcom.com',
#     request_token_url=None,
#     access_token_method='POST',
#     access_token_url='https://sandbox-api.dexcom.com/v1/oauth2/token',
#     authorize_url='https://sandbox-api.dexcom.com/v1/oauth2/login',
#     request_token_params={
#         'client_id': client_id,
#         'redirect_uri': redirect,
#         'response_type': 'code',
#         'scope': 'offline_access'
#         }
# )

from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect, session, url_for
from flask.json import jsonify
import os

app = Flask(__name__)


# This information is obtained upon registration of a new dexcom OAuth
# application here: https://dexcom.com/settings/applications/new
client_id = os.environ['DEX_CLIENT_ID']
client_secret = os.environ['DEX_CLIENT_SECRET']
authorization_base_url = 'https://sandbox-api.dexcom.com/v1/oauth2/login'
token_url = 'https://sandbox-api.dexcom.com/v1/oauth2/login'


@app.route("/")
def demo():
    """Step 1: User Authorization.

    Redirect the user/resource owner to the OAuth provider (i.e. Dexcom)
    using an URL with a few key OAuth parameters.
    """
    dexcom = OAuth2Session(client_id)
    authorization_url, state = dexcom.authorization_url(authorization_base_url)

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state
    return redirect(authorization_url)


# Step 2: User authorization, this happens on the provider.

@app.route("/callback", methods=["GET"])
def callback():
    """ Step 3: Retrieving an access token.

    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """

    dexcom = OAuth2Session(client_id, state=session['oauth_state'])
    token = dexcom.fetch_token(token_url, client_secret=client_secret,
                              redirect_uri=redirect, authorization_response=request.url)

    # At this point you can fetch protected resources but lets save
    # the token and show how this is done from a persisted token
    # in /profile.
    session['oauth_token'] = token

    return redirect(url_for('.profile'))


@app.route("/profile", methods=["GET"])
def profile():
    """Fetching a protected resource using an OAuth 2 token.
    """
    dexcom = OAuth2Session(client_id, token=session['oauth_token'])
    return jsonify(dexcom.get('https://api.dexcom.com/user').json())


if __name__ == "__main__":
    # This allows us to use a plain HTTP callback
    os.environ['DEBUG'] = "1"

    app.secret_key = os.urandom(24)
    app.run(debug=True)
