from flask import Blueprint, render_template, session, url_for, redirect
from .auth import hacker_login_required
from .common import flasher
from .db import get_db
from json import dumps
import time

bp = Blueprint('hacker', __name__, url_prefix='/hacker')

def capitalize_login_provider():
    if session['login_type'] == 'mlh':
        return 'MLH'
    elif session['login_type'] == 'github':
        return 'Github'

@bp.route('/import/mlh')
@hacker_login_required
def init_mlh():
    c = get_db().cursor()
    print('mlh_id: ', session['mlh_info'])
    mlh_id = session['mlh_info']['id']
    email  = session['mlh_info']['email']

    school_name = session['mlh_info']['school']['name'] if 'name' in session['mlh_info']['school'] else None

    c.execute('SELECT COUNT(1) FROM Applicants WHERE email=?', (email,))
    if c.fetchone()[0] != 1:
        # first login, init profile
        c.execute('''
            INSERT INTO Applicants
                (admin, adult, completed, admitted, user_id, email, contact_email, mlh_json, first_name, last_name, timestamp, gender, school)
                VALUES (0,1,0,0,?,?,?,?,?,?,?,?,?)
        ''', (
            'mlh:' + str(mlh_id),
            session['mlh_info']['email'],
            session['mlh_info']['email'],
            dumps(session['mlh_info']),
            session['mlh_info']['first_name'],
            session['mlh_info']['last_name'],
            int(time.time() * 1000),
            session['mlh_info']['gender'].lower(),
            school_name
        ))
        c.connection.commit()
        flasher('Imported data from MLH. Please double check it\'s correct!', color='success')
    else:
        pass
    # not first login, we're good

    session['email'] = email

    return redirect(url_for('hacker.application'))

@bp.route('/import/gh')
@hacker_login_required
def init_gh():
    c = get_db().cursor()

    print('gh_info', session['gh_info'])
    email = session['gh_info']['email']

    c.execute('SELECT COUNT(1) FROM Applicants WHERE email=?', (email,))
    if c.fetchone()[0] != 1:
        # first login, init profile
        c.execute('''
            INSERT INTO Applicants
                (admin, adult, completed, admitted, user_id, email, contact_email, gh_json, timestamp)
            VALUES (0,1,0,0,?,?,?,?,?)
        ''', (
            'gh:' + str(session['gh_info']['id']),
            email,
            email,
            dumps(session['gh_info']),
            int(time.time() * 1000)
        ))
        c.connection.commit()

        flasher('Imported data from Github. Please double check it\'s correct!', color='success')
    else:
        pass
    # we should load the profile maybe

    session['email'] = email
    return redirect(url_for('hacker.application'))


def resolve_application(email):
    c = get_db().cursor()
    c.execute('SELECT * FROM Applicants WHERE email=?', (email,))
    row = c.fetchone()

    print(row.keys())

    row_text = {}
    for key in row.keys():
        row_text[key] = '' if row[key] is None else row[key]

    return row, row_text


@bp.route('/application')
@hacker_login_required
def application():
    appl, appl_text = resolve_application(session['email'])
    return render_template(
        'hacker/form.html',
        appl=appl_text,
        login_type=capitalize_login_provider()
    )

@bp.route('/application/submit', methods=['POST'])
@hacker_login_required
def submit_application():
    return 'no'

@bp.route('/application/save', methods=['POST'])
@hacker_login_required
def save_application():
    return 'ok'
