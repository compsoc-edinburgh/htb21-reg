from flask import Flask
import os
import json

def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY='dev',
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, 'votes.sqlite'),
    )

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # try to load the test configuration
    if test_config is None:
        # load the instance config, if it exists, when not testing
        config_path = os.path.join(app.instance_path, 'config.json')
        config = json.load(open(config_path, 'r'))
        app.config.update(config)
    else:
        # load the test config if passed in
        app.config.update(test_config)


    # register the database commands
    from . import db
    db.init_app(app)

    # apply the blueprints to the app
    from . import auth, dashboard, actions
    app.register_blueprint(auth.bp)
    auth.register_google_bp(app) # hax
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(actions.bp)

    # initialize the google blueprint
    


    # Apply CORS rules to the entire application
    # IMHO it's not worth configuring properly ATM
    #CORS(app, origin='*')

    return app



