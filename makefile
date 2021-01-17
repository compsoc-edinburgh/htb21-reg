STAGING = staging
VIRTUALENV = env_h21reg
DOCKER_TAG_NAME = htb21-reg
REMOTE = compsoc-admin@bucket.comp-soc.com
REMOTE_DESTINATION = ~/voter

all: run

run:
	source ${VIRTUALENV}/bin/activate && \
		OAUTHLIB_INSECURE_TRANSPORT=1    \
		OAUTHLIB_RELAX_TOKEN_SCOPE=1     \
		FLASK_DEBUG=1	                 \
		FLASK_ENV=development    \
		python -m flask run

init-db:
	source ${VIRTUALENV}/bin/activate && \
		FLASK_DEBUG=0                    \
		FLASK_ENVIRONMENT=development    \
		python -m flask init-db

clean:
	rm -f ${STAGING}/${DOCKER_TAG_NAME}.tar.gz

upload: clean
	mkdir -p ${STAGING}
	docker build . -t ${DOCKER_TAG_NAME}
	docker save ${DOCKER_TAG_NAME} -o ${STAGING}/${DOCKER_TAG_NAME}.tar.gz
	scp ${STAGING}/${DOCKER_TAG_NAME}.tar.gz ${REMOTE}:${REMOTE_DESTINATION}/${DOCKER_TAG_NAME}

connect:
	ssh ${REMOTE}

deploy: upload
	ssh -t ${REMOTE} 'cd ${REMOTE_DESTINATION}; sudo docker-compose stop; sudo docker load -i ${DOCKER_TAG_NAME}.tar.gz; sudo docker-compose up -d;'


init-deploy:
	ssh -t ${REMOTE} 'mkdir -p ${REMOTE_DESTINATION}'
	scp docker-compose.yml ${REMOTE}:${REMOTE_DESTINATION}


prod:
	FLASK_DEBUG=0 python -m flask run
