from flask import Blueprint, url_for, redirect, request, jsonify, Response, make_response, send_file, current_app
from .common import get_config, row_to_obj, rows_to_objs
from .data import create_csv
from .db import get_db
from json import dumps
import functools
import bcrypt
import time

bp = Blueprint('service_api', __name__, url_prefix='/api/v1')

def create_response(obj, ok=True, message=None, code=None):
    out = {}
    out['ok'] = ok
    if message is not None:
        out['message'] = message
    if code is None:
        out['code'] = 200 if ok else 400
    else:
        out['code'] = code
    out['data'] = obj
    return make_response(jsonify(out), out['code'])


def validate_auth(auth_slug):
    if auth_slug is None:
        return False

    if len(auth_slug) <= 8:
        return False

    # ok length to chop off the "Bearer " from the start
    auth_slug = auth_slug[7:]

    # check if we can split into api key and api secret
    if not '/' in auth_slug:
        return False


    # extract key and secret
    auth_slug = auth_slug.split('/')
    api_key    = auth_slug[0]
    api_secret = auth_slug[1].encode('ascii')


    # get database cursor
    c = get_db().cursor()
    c.execute('''
        SELECT api_secret, active
            FROM Services
            WHERE api_key=?
    ''', (api_key,))


    # check if there is a service with the specified key
    svc = c.fetchone()
    if svc is None:
        print('no such service')
        return False

    # validate bcrypt
    if not bcrypt.checkpw(api_secret, svc['api_secret']):
        print('bcrypt failure')
        return False

    # check it's not disabled
    if svc['active'] == 0:
        print('inactive service')
        return False

    # successful auth, update lastused
    c.execute('''
        UPDATE Services
            SET last_used=?
            WHERE api_key=?
    ''', (time.time(), api_key))

    c.connection.commit()

    return True


def service_auth_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        try:
            authed = validate_auth(request.headers.get('Authorization'))
        except Exception as e:
            raise
            print(e)
            authed = False

        if not authed:
            response = make_response(jsonify({
                'ok': False,
                'message': 'unauthorized',
                'code': 401
            }), 401)
            return response
        return view(**kwargs)

    return wrapped_view


@bp.app_errorhandler(404)
def api_404(e):
    return create_response(
        None,
        ok=False,
        code=404,
        message='method not found'
    )



@bp.route('/config')
@service_auth_required
def api_config():
    '''
    Download the current application's configuration. This has the form:

    <pre>
    {
        "applications_open": "<timestamp>",
        "applications_dline": "<timestamp>",
        "event_start": "<timestamp>"
    }</pre>
    '''
    db = get_db()
    cfg = get_config(db)
    obj = row_to_obj(cfg)
    del obj['id']

    return create_response(obj)


@bp.route('/backup')
@service_auth_required
def api_download_backup():
    '''
    Download the database as a SQLite file.
    '''
    return send_file(current_app.config['DATABASE'])


@bp.route('/applicants/by_email')
@service_auth_required
def api_get_by_email():
    '''
    Get a user by their email.

    Requires a query parameter `email`, for example for email `test@example.com` the query is `email=test%40example.com`.
    '''
    email = request.args.get('email')
    if email is None:
        return create_response({}, ok=False, message=f'No parameter "email"!')

    c = get_db().cursor()
    c.execute('''
        SELECT * FROM Applicants WHERE email=?
    ''', (email,))

    usr = c.fetchone()
    if usr is None:
        return create_response({}, ok=False, message=f'No such user {email}', code=404)

    return create_response(row_to_obj(usr))


@bp.route('/applicants/by_id')
@service_auth_required
def api_get_by_id():
    '''
    Get a user by their `user_id`.

    Requires a query parameter `id`, for example for id `gh:12345` the query is `id=gh%3A12345`.
    '''
    uid = request.args.get('id')
    if uid is None:
        return create_response({}, ok=False, message=f'No parameter "id"!')

    c = get_db().cursor()
    c.execute('''
        SELECT * FROM Applicants WHERE user_id=?
    ''', (uid,))

    usr = c.fetchone()
    if usr is None:
        return create_response({}, ok=False, message=f'No such user {uid}', code=404)

    return create_response(row_to_obj(usr))


@bp.route('/applicants/all/json')
@service_auth_required
def api_get_all_applicants():
    '''
    Returns a JSON array of all applicants in the database.

    Adding a query parameter `completed=true` will filter for only completed applications.
    '''
    c = get_db().cursor()

    if (request.args.get('completed') == 'true'):
        c.execute('''
            SELECT * FROM Applicants WHERE completed=1
        ''')
    else:
        c.execute('''
            SELECT * FROM Applicants
        ''')

    rows = c.fetchall()
    if rows is None:
        rows = []
    else:
        rows = rows_to_objs(rows)

    return create_response(rows)


@bp.route('/applicants/all/csv')
@service_auth_required
def api_get_all_applicants_csv():
    '''
    Return a CSV version of all completed applicants.
    '''
    db = get_db()
    csv = create_csv(db)

    return Response(
        csv,
        mimetype='text/csv'
    )

@bp.route('/applicants/admit', methods=['POST'])
@service_auth_required
def api_admit():
    '''
    Set's a user's admission status by `user_id`, via a POST request.

    JSON body:
    <pre>
    {
        "app_id": "applicant_id",
        "admit": true, // or false
    }</pre>
    '''

    app_id = request.json['app_id'] if 'app_id' in request.json else None
    admit  = request.json['admit']  if 'admit'  in request.json else None

    if app_id is None or admit is None:
        return create_response({}, ok=False, message='Must have both app_id and admit!')


    c = get_db().cursor()
    c.execute('''
        UPDATE Applicants
            SET admitted=?
            WHERE user_id=?
    ''', [
        admit,
        app_id
    ])

    c.connection.commit()
    return create_response({})


@bp.route('/invites/create', methods=['POST'])
@service_auth_required
def api_invite_create():
    '''
    Creates an invite from POSTed JSON.

    JSON body:
    <pre>
    {
        "app_id": "applicant_id",
        "service": "Service Name",
        "code": "(optional) code",
        "link": "(optional) link",
    }</pre>
    '''

    link = request.json['link'] if 'link' in request.json else None
    code = request.json['code'] if 'code' in request.json else None

    if link is None and code is None:
        return create_response({}, ok=False, message='Must have either link or code!')

    c = get_db().cursor()
    c.execute('''
        INSERT INTO Invites (app_id, service, link, code)
        VALUES (?,?,?,?)
    ''', [
        request.json['app_id'],
        request.json['service'],
        link,
        code
    ])

    c.connection.commit()

    return create_response({})

@bp.route('/invites/list')
@service_auth_required
def api_invite_list():
    '''
    List all the invites in the database.

    With an optional parameter `id`, this will return only the invites for the specified `user_id`.
    '''

    c = get_db().cursor()

    if request.args.get('id') is not None:
        c.execute('''
            SELECT * FROM Invites WHERE app_id=?
        ''', [request.args.get('id')])
    else:
        c.execute('''
            SELECT * FROM Invites
        ''')

    rows = c.fetchall()
    if rows is None:
        rows = []

    return create_response(rows_to_objs(rows))

api_routes = [
    api_config,
    api_download_backup,
    api_get_by_id,
    api_get_by_email,
    api_get_all_applicants,
    api_get_all_applicants_csv,
    api_admit,
    api_invite_create,
    api_invite_list
]
