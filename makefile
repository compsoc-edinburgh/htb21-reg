all: run


run:
	source env_voter/bin/activate && OAUTHLIB_INSECURE_TRANSPORT=1 OAUTHLIB_RELAX_TOKEN_SCOPE=1 FLASK_DEBUG=1 FLASK_ENVIRONMENT=development python -m flask run

init-db:
	source env_voter/bin/activate && FLASK_DEBUG=0 FLASK_ENVIRONMENT=development python -m flask init-db

prod:
	FLASK_DEBUG=0 python -m flask run
