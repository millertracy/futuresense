from flask import Flask

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return 'Click here: <a href="https://sandbox-api.dexcom.com/v1/oauth2/login?client_id=eAZxmMneto6aXUbUCVA4h29CT6RKeqvK&redirect_uri=34.215.61.65&response_type=code&scope=offline_access"> link! </a>'


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
