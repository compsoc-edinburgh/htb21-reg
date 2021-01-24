FROM python:alpine3.7

WORKDIR /app

RUN apk add make alpine-sdk libffi-dev --no-cache
RUN pip install gunicorn
COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD gunicorn -b 0.0.0.0:5000 --access-logfile - --error-logfile - 'app:create_app()'
