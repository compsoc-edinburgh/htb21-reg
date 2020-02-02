#! /bin/bash

source env_voter/bin/activate
OAUTHLIB_INSECURE_TRANSPORT=1 OAUTHLIB_RELAX_TOKEN_SCOPE=1 FLASK_DEBUG=1 python -m flask run

