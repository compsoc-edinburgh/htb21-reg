all: run


run:
	bash run.sh

prod:
	FLASK_DEBUG=0 python -m flask run
