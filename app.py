from flask import Flask, redirect, url_for, render_template
from flask_dance.contrib.google import make_google_blueprint, google
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
import requests
import json

secrets = json.load(open('instance/secret.json', 'r'))

app = Flask(__name__)
app.secret_key = secrets['app_secret_key']
blueprint = make_google_blueprint(
    client_id=secrets['client_id'],
    client_secret=secrets['client_secret'],
    scope=['profile', 'email']
)
app.register_blueprint(blueprint, url_prefix='/login')

# magic happens here
def email_valid(email):
    if email.endswith('@comp-soc.com') or email.endswith('@hacktheburgh.com') or email.endswith('@sigint.mx'):
        return True
    return False

@app.route('/')
def index():
    if google.authorized:
        return redirect(url_for('profile'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    # retrieve token
    token = blueprint.token["access_token"]

    try:
        # revoke permission from Google's API
        resp = google.post(
            "https://accounts.google.com/o/oauth2/revoke",
            params={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.ok, resp.text
    except TokenExpiredError as e:
        print('token expired, ignoring')
    del blueprint.token  # Delete OAuth token from storage
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if not google.authorized:
        return redirect(url_for('google.login'))
    # print(dir(google.get))
    # print('google token: {}'.format(google.token[u'access_token']))
    resp = requests.get(
            'https://people.googleapis.com/v1/people/me',
            params={
                'personFields': 'names,emailAddresses,photos'
            },
            headers={
                'Authorization': 'Bearer {}'.format(google.token[u'access_token'])
            })

    person_info = resp.json()

    profile = {
        'email': person_info[u'emailAddresses'][0][u'value'],
        'name': person_info[u'names'][0][u'displayName'],
        'image': person_info[u'photos'][0][u'url'].split('=')[0] # remove the 100px limit (ends with =s100)
    }
    
    return render_template('profile.html',
            profile=profile,
            valid=email_valid(profile['email'])
    )

if __name__ == '__main__':
    app.run()
