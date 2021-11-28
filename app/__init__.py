from werkzeug.middleware.proxy_fix import ProxyFix
import json
import os
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""

    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # load from test_config, instance/{env}.json
    if test_config is None:
        app.config.from_file(
            "%s.json" % os.environ.get("FLASK_ENV", default="production"),
            load=json.load,
        )
    else:
        app.config.from_mapping(test_config)

    # populate database path if it's not already
    if "DATABASE" not in app.config:
        app.config["DATABASE"] = os.path.join(
            app.instance_path, "registrations.sqlite")

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # register the database commands
    from . import db

    db.init_app(app)

    # apply the blueprints to the app
    from . import auth, dashboard, actions, landing, hacker, services, service_api

    app.register_blueprint(auth.bp)
    auth.register_auth_bps(app)

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(actions.bp)
    app.register_blueprint(landing.bp)
    app.register_blueprint(services.bp)
    app.register_blueprint(service_api.bp)
    app.register_blueprint(hacker.bp)

    @app.errorhandler(404)
    def app_404(route):
        return render_template("404.html")

    # TODO: CORS rules

    return app
