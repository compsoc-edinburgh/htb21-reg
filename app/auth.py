# -- this is a disaster. --

from flask import Flask, redirect, url_for, render_template, Blueprint, session, current_app
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.consumer import OAuth2ConsumerBlueprint
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
import functools
import requests
import json
import os
from flask.globals import LocalProxy, _lookup_app_object
from pprint import pprint
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

bp = Blueprint('auth', __name__)

google_bp = None
mlh_bp = None
github_bp = None
mymlh = None

def register_google_bp(app):
    global google_bp # NOT GOOD
    google_bp = make_google_blueprint(
        client_id=os.environ['GOOGLE_CLIENT_ID'],
        client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
        scope=['profile', 'email'],
        redirect_to='auth.profile'
    )
    app.register_blueprint(google_bp, url_prefix='/oauth/admin')


def register_mlh_bp(app):
    global mlh_bp
    global mymlh

    mlh_bp = OAuth2ConsumerBlueprint(
        'mymlh', __name__,
        client_id=os.environ['MLH_CLIENT_ID'],
        client_secret=os.environ['MLH_CLIENT_SECRET'],
        base_url='https://my.mlh.io',
        token_url='https://my.mlh.io/oauth/token',
        scope=['email','education', 'demographics'],
        authorization_url='https://my.mlh.io/oauth/authorize',
        redirect_to='auth.hacker_profile'
    )

    @mlh_bp.before_app_request
    def set_applocal_session():
        ctx = stack.top
        ctx.mymlh_oauth = mlh_bp.session

    mymlh = LocalProxy(functools.partial(_lookup_app_object, "mymlh_oauth"))
    app.register_blueprint(mlh_bp, url_prefix='/oauth/hacker')

def register_github_bp(app):
    global github_bp
    github_bp = make_github_blueprint(
        client_id=os.environ['GITHUB_CLIENT_ID'],
        client_secret=os.environ['GITHUB_CLIENT_SECRET'],
        scope='user:email',
        redirect_to='auth.hacker_profile_gh'
    )

    app.register_blueprint(github_bp, url_prefix='/oauth/hacker')


@bp.route('/')
def index():
    if google.authorized:
        return redirect(url_for('auth.profile'))
    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    # retrieve token

    try:
        token = google_bp.token["access_token"]

        # revoke permission from Google's API
        resp = google.post(
            "https://accounts.google.com/o/oauth2/revoke",
            params={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.ok, resp.text

    except TokenExpiredError as e:
        print('token expired, ignoring')
    except TypeError as e:
        print('probably fine too')

    try:
        del google_bp.token  # Delete OAuth token from storage
    except Exception as e:
        print('probably also fine')
    return redirect(url_for('landing.index'))


def admin_login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not google.authorized:
            return redirect(url_for('google.login'))
        return view(**kwargs)

    return wrapped_view

def hacker_login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not mymlh.authorized and not github.authorized:
            return redirect(url_for('landing.index'))
        return view(**kwargs)

    return wrapped_view


@bp.route('/profile')
@admin_login_required
def profile():
    # hacky, but this pins the google profile information to the session
    resp = requests.get(
            'https://people.googleapis.com/v1/people/me',
            params={
                'personFields': 'names,emailAddresses,photos'
            },
            headers={
                'Authorization': 'Bearer {}'.format(google.token[u'access_token'])
            })

    person_info = resp.json()
    pprint(person_info)

    profile = {
        'email': person_info[u'emailAddresses'][0][u'value'],
        'name': person_info[u'names'][0][u'displayName'],
        'image': person_info[u'photos'][0][u'url'].split('=')[0] # remove the 100px limit (ends with =s100)
    }

    session['name'] = profile['name']
    session['email'] = profile['email']
    session['image'] = profile['image']

    return redirect(url_for('dashboard.rate_queue'))

# -- MLH profile info --

@bp.route('/hacker')
@hacker_login_required
def hacker_profile():
    session['login_type'] = 'mlh'
    profile = get_hacker_mlh_profile()
    session['email'] = profile['email']
    session['mlh_info'] = profile
    return redirect(url_for('hacker.init_mlh'))

@bp.route('/hacker/logout')
@hacker_login_required
def hacker_logout():
    try:
        del mlh_bp.token
    except:
        pass
    try:
        del github_bp.token
    except:
        pass

    session.clear()
    return redirect(url_for('landing.index'))

def get_hacker_mlh_profile():
    resp = mlh_bp.session.get('/api/v3/user.json')
    print(resp.json())
    return resp.json()['data']


# -- GH profile info --

def get_hacker_gh_profile():
    resp = github.get('/user').json()
    resp_emails = github.get('/user/emails')
    email = [addr['email'] for addr in resp_emails.json() if addr['primary']][0]
    
    resp['email'] = email

    return resp

@bp.route('/hacker/github')
@hacker_login_required
def hacker_profile_gh():
    session['login_type'] = 'github'
    profile = get_hacker_gh_profile()
    session['gh_info'] = profile
    session['email'] = profile['email']

    return redirect(url_for('hacker.init_gh'))

