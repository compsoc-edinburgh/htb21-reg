from flask import _app_ctx_stack as stack
from flask.globals import LocalProxy, _lookup_app_object
from functools import partial
from flask_dance.consumer import OAuth2ConsumerBlueprint


def make_mymlh_blueprint(
    client_id=None,
    client_secret=None,
    *,
    scope=None,
    redirect_url=None,
    redirect_to=None,
    login_url=None,
    authorized_url=None,
    session_class=None,
    storage=None,
    rule_kwargs=None,
):
    mymlh_bp = OAuth2ConsumerBlueprint(
        "mymlh",
        __name__,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        base_url="https://my.mlh.io",
        authorization_url="https://my.mlh.io/oauth/authorize",
        token_url="https://my.mlh.io/oauth/token",
        redirect_url=redirect_url,
        redirect_to=redirect_to,
        login_url=login_url,
        authorized_url=authorized_url,
        session_class=session_class,
        storage=storage,
        rule_kwargs=rule_kwargs,
    )
    mymlh_bp.from_config["client_id"] = "MYMLH_OAUTH_CLIENT_ID"
    mymlh_bp.from_config["client_secret"] = "MYMLH_OAUTH_CLIENT_SECRET"

    @mymlh_bp.before_app_request
    def set_applocal_session():
        ctx = stack.top
        ctx.mymlh_oauth = mymlh_bp.session

    return mymlh_bp


mymlh = LocalProxy(partial(_lookup_app_object, "mymlh_oauth"))
