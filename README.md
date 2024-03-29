# HTB 7 Registration Portal

## what?

This is a tool to allow compsoc committee members to sign into internal applications, using our existing google admin platform.

## why?

This lets us greatly reduce the overhead of launching new applications, as we can shift account management up to the long-suffering administrator.

## how?

This is just a demo application, intended as a starting off point for creating new applications. You'll need to create a project on (ideally CompSoc's) [GCP](https://console.cloud.google.com/), issue a client ID and secret for a web oauth application, and properly configure the callback urls.

More verbosely:

1) Log into [GCP](https://console.cloud.google.com), and create a new project by clicking th project header on the title bar and clicking "New Project." Ideally this should be created under the "comp-soc.com" domain.

2) Once you've created the project, go to the sidebar > APIs & Services > Credentials. You'll need to add routes like so:

![credentials](/docs/credentials.png?raw=true)
![routes](/docs/routes.png?raw=true)

Routes for this application:

```
# Google
http://localhost:5000/oauth/admin/google/authorized
https://registration.2021.hacktheburgh.com/oauth/admin/google/authorized
```

3) You'll also need to enable access to the People API, which is used to retrieve a profile photo and other information. This can be done through the sidebar > APIs & Services > Library portal.

Once you've done that, you'll need to create your json configuration file in `instance/development.json`:

```json
{
    "client_id": "YOUR_GOOGLE_CLIENT_ID",
    "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
    "app_secret_key": "SOME_RANDOM_STRING"
}
```

Then you should be good to go! Initialise the database with and start a development server with:

```
$ export FLASK_ENV=development
$ python -m flask init-db
$ OAUTHLIB_INSECURE_TRANSPORT=1 OAUTHLIB_RELAX_TOKEN_SCOPE=1 python -m flask run
```

When deploying, you just need to use `docker-compose up -d`. We deploy it behind an nginx proxy.

# who?

This was written in a fit of procrastination by [@pkage](//kage.dev).
