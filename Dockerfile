FROM python:alpine3.7

COPY . /app
WORKDIR /app

RUN apk add make

RUN pip install -r requirements.txt

EXPOSE 5000
CMD make prod
