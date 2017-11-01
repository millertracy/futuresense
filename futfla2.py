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
from flask import Flask, request, redirect, session, url_for, render_template
from flask.json import jsonify
import os
import boto3
from futuresense import FutureSense


app = Flask(__name__)

#aws_client = boto3.client('cognito-identity')

# Client keys are stored in .bashrc as environment variables
client_id = os.environ['DEX_CLIENT_ID']
client_secret = os.environ['DEX_CLIENT_SECRET']
authorization_base_url = 'https://api.dexcom.com/v1/oauth2/login'
token_url = 'https://api.dexcom.com/v1/oauth2/login'
redirect_u = 'http://theglucoseguardian.com/callback'
scp = ['offline_access']

@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
@app.route("/index.html", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/about", methods=["GET"])
@app.route("/about.html", methods=["GET"])
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET"])
@app.route("/contact.html", methods=["GET"])
def contact():
    return render_template("contact.html")

@app.route("/register", methods=["GET"])
@app.route("/register.html", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/signin", methods=["GET"])
@app.route("/signin.html", methods=["GET"])
def signin():
    return render_template("signin.html")

@app.route("/authorize", methods=["GET", "POST"])
def authorize():
    """Step 1: User Authorization.

    Redirect the user/resource owner to the OAuth provider (i.e. Dexcom)
    using an URL with a few key OAuth parameters.
    """
    dexcom = OAuth2Session(client_id, redirect_uri=redirect_u, scope=scp)
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
    authcode = request.args.get('code', '')
    fs = FutureSense(user='djo', auth=authcode, sandbox=False)
    #fs.get_all(all_reps=4)

    return str(authcode)
    # dexcom = OAuth2Session(client_id, state=session['oauth_state'], redirect_uri=redirect, scope=scp)
    # token = dexcom.fetch_token(token_url, client_secret=client_secret,
    #                           redirect_uri=redirect_u, authorization_response=request.url)
    # At this point you can fetch protected resources but lets save
    # the token and show how this is done from a persisted token
    # in /profile.
    # session['oauth_token'] = token
    #
    # return redirect(url_for('.profile'))

# http://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html
# @app.route("/profile", methods=["GET"])
# def profile():
#     """Fetching a protected resource using an OAuth 2 token.
#     """
#     dexcom = OAuth2Session(client_id, token=session['oauth_token'], redirect_uri=redirect_u, scope=scp)
#     return jsonify(dexcom.get('https://api.dexcom.com/v1/oauth2/login').json())

if __name__ == "__main__":
    # This allows us to use a plain HTTP callback
    os.environ['DEBUG'] = "1"

    app.secret_key = os.urandom(24)
    app.run(debug=True)
