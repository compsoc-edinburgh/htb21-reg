from flask import (
    Flask,
    redirect,
    url_for,
    render_template,
    Blueprint,
    session,
    current_app,
)
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from .mymlh import make_mymlh_blueprint, mymlh
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

bp = Blueprint("auth", __name__, url_prefix="/auth")


def register_auth_bps(app):
    """Register all Oauth blueprints"""

    # Google
    app.register_blueprint(make_google_blueprint(
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        scope=["profile", "email"],
        redirect_to="auth.profile",
    ), url_prefix="/oauth/admin")

    # MLH
    app.register_blueprint(make_mymlh_blueprint(
        client_id=app.config["MLH_CLIENT_ID"],
        client_secret=app.config["MLH_CLIENT_SECRET"],
        scope=[
            "email", "education", "demographics"],
        redirect_to="auth.hacker_profile"
    ), url_prefix="/oauth/hacker")

    # GitHub
    app.register_blueprint(make_github_blueprint(
        client_id=app.config["GITHUB_CLIENT_ID"],
        client_secret=app.config["GITHUB_CLIENT_SECRET"],
        scope="user:email",
        redirect_to="auth.hacker_profile",
    ), url_prefix="/oauth/hacker")


def admin_login_required(view):
    """View decorator that redirects anonymous users to the login page."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not google.authorized:
            return redirect(url_for("google.login"))
        return view(**kwargs)

    return wrapped_view


def hacker_login_required(view):
    """View decorator that redirects anonymous users to the login page."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        print(mymlh.authorized)
        if not mymlh.authorized and not github.authorized:
            return redirect(url_for("landing.index"))
        return view(**kwargs)

    return wrapped_view


@bp.route("/")
def index():
    if google.authorized:
        return redirect(url_for("auth.profile"))
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    """Log out an admin (google) account, invalidating the oauth2 token"""

    try:
        token = google.token["access_token"]

        # revoke permission from Google's API
        resp = google.post(
            "https://accounts.google.com/o/oauth2/revoke",
            params={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.ok, resp.text

    except TokenExpiredError as e:
        pass  # Token expired, No problem
    except TypeError as e:
        pass  # Apparently also fine

    try:
        # Delete OAuth token from storage
        del google.token
    except Exception as e:
        pass  # No token to delete

    return redirect(url_for("landing.index"))


@bp.route("/profile")
@admin_login_required
def profile():
    # Pin google profile information to the session
    resp = requests.get(
        "https://people.googleapis.com/v1/people/me",
        params={"personFields": "names,emailAddresses,photos"},
        headers={"Authorization": "Bearer {}".format(
            google.token["access_token"])},
    )

    person_info = resp.json()

    profile = {
        "email": person_info["emailAddresses"][0]["value"],
        "name": person_info["names"][0]["displayName"],
        # Remove 100 pixel parameter
        "image": person_info["photos"][0]["url"].replace("=s100", "")
    }

    session["name"] = profile["name"]
    session["email"] = profile["email"]
    session["image"] = profile["image"]

    return redirect(url_for("dashboard.rate_queue"))


# -- MLH profile info --

def get_hacker_mlh_profile():
    resp = mymlh.session.get("/api/v3/user.json")
    return resp.json()["data"]


def get_hacker_gh_profile():
    resp = github.get("/user").json()
    resp_emails = github.get("/user/emails")
    email = [addr["email"]
             for addr in resp_emails.json() if addr["primary"]][0]

    resp["email"] = email

    return resp


@bp.route("/hacker")
@hacker_login_required
def hacker_profile():
    mlh = mymlh

    if mymlh.authorized:
        # MLH
        session["login_type"] = "mlh"
        profile = get_hacker_mlh_profile()
        session["email"] = profile["email"]
        session["mlh_info"] = profile
        return redirect(url_for("hacker.init_mlh"))
    else:
        # GitHub
        session["login_type"] = "github"
        profile = get_hacker_gh_profile()
        session["gh_info"] = profile
        session["email"] = profile["email"]

        return redirect(url_for("hacker.init_gh"))


@bp.route("/hacker/logout")
@hacker_login_required
def hacker_logout():
    try:
        del mymlh.token
    except:
        pass
    try:
        del current_app.blueprints['github'].token
    except:
        pass

    session.clear()
    return redirect(url_for("landing.index"))
