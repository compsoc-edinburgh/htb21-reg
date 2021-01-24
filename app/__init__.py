from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template
import os
import json
from werkzeug.middleware.proxy_fix import ProxyFix



def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""

    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY=os.environ['APP_SECRET_KEY'],
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, 'registrations.sqlite'),
    )

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    

    # register the database commands
    from . import db
    db.init_app(app)

    # apply the blueprints to the app
    from . import auth, dashboard, actions, landing, hacker, services
    app.register_blueprint(auth.bp, url_prefix='/auth')
    auth.register_google_bp(app) # hax
    auth.register_mlh_bp(app)    # double hax
    auth.register_github_bp(app) # triple hax

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(actions.bp)
    app.register_blueprint(landing.bp)
    app.register_blueprint(services.bp)
    app.register_blueprint(hacker.bp)


    @app.errorhandler(404)
    def app_404(route):
        return render_template('404.html')


    # Apply CORS rules to the entire application
    # IMHO it's not worth configuring properly ATM
    #CORS(app, origin='*')

    return app



