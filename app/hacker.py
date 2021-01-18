from flask import Blueprint, render_template, session, url_for, redirect, request
from .auth import hacker_login_required
from .common import flasher, get_config
from .db import get_db
from json import dumps
import arrow
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
                (verified, admin, adult, completed, admitted, user_id, email, contact_email, mlh_json, first_name, last_name, timestamp, gender, school)
                VALUES (1,0,0,0,0,?,?,?,?,?,?,?,?,?)
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
                (verified, admin, adult, completed, admitted, user_id, email, contact_email, gh_json, timestamp)
            VALUES (1,0,0,0,0,?,?,?,?,?)
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

    row_text = {}
    for key in row.keys():
        row_text[key] = '' if row[key] is None else row[key]

    return row, row_text


@bp.route('/application')
@hacker_login_required
def application():
    appl, appl_text = resolve_application(session['email'])

    if appl['completed']:
        completed_time = arrow.get(appl['completed_time']).format('MMM D, YYYY hh:mm a')
    else:
        completed_time = ''

    return render_template(
        'hacker/form.html',
        appl=appl_text,
        completed_time=completed_time,
        login_type=capitalize_login_provider()
    )


@bp.route('/application/submit', methods=['POST'])
@hacker_login_required
def submit_application():
    db = get_db()
    c = db.cursor()

    #appl, _ = resolve_application(session['email'])
    #if appl['completed']:
    #    flasher('Can\'t re-submit, application already submitted!', color='warning')
    #    return redirect(url_for('hacker.application'))

    cfg = get_config(db)
    if (cfg['applications_dline'] <= time.time()):
        flasher('Application deadline has passed!', color='danger')
        return redirect(url_for('hacker.application'))

    try:
        # checkboxes
        cb_gdpr         = 'gdpr' in request.form and request.form['gdpr'] == 'on'
        cb_mlh_coc      = 'mlh_coc' in request.form and request.form['mlh_coc'] == 'on'
        cb_adult        = 'adult' in request.form and request.form['adult'] == 'on'
        cb_hackuk_admin = 'hackuk_admin' in request.form and request.form['hackuk_admin'] == 'on'
        cb_hackuk_email = 'hackuk_email' in request.form and request.form['hackuk_email'] == 'on'

        dd_gradYear = request.form['gradYear'] if 'gradYear' in request.form else None
        dd_shirt_size = request.form['shirt_size'] if 'shirt_size' in request.form else None

        c.execute('''
            UPDATE Applicants
                SET first_name=?,
                    last_name=?,
                    contact_email=?,
                    school=?,
                    gradYear=?,
                    shirt_size=?,
                    address_line_1=?,
                    address_line_2=?,
                    address_line_3=?,
                    address_city=?,
                    address_region=?,
                    address_country=?,
                    address_pcode=?,
                    description=?,
                    essay=?,
                    gdpr=?,
                    mlh_coc=?,
                    adult=?,
                    hackuk_admin=?,
                    hackuk_email=?,
                    completed=1,
                    completed_time=?
                WHERE
                    email=?
        ''',[
            request.form['first_name'],
            request.form['last_name'],
            request.form['contact_email'],
            request.form['school'],
            dd_gradYear,
            dd_shirt_size,
            request.form['address_line_1'],
            request.form['address_line_2'],
            request.form['address_line_3'],
            request.form['address_city'],
            request.form['address_region'],
            request.form['address_country'],
            request.form['address_pcode'],
            request.form['description'],
            request.form['essay'],
            cb_gdpr,
            cb_mlh_coc,
            cb_adult,
            cb_hackuk_admin,
            cb_hackuk_email,
            time.time(),
            session['email']
        ])
        c.connection.commit()

        flasher('Submitted successfully!', color='success')
    except Exception as e:
        raise e
        print(e)
        flasher('Something went wrong! Please contact tech@hacktheburgh.com.', color='danger')

    return redirect(url_for('hacker.application'))

@bp.route('/application/save', methods=['POST'])
@hacker_login_required
def save_application():
    db = get_db()
    c = db.cursor()

    appl, _ = resolve_application(session['email'])
    if appl['completed']:
        flasher('Can\'t save changes, application already submitted!', color='warning')
        return redirect(url_for('hacker.application'))

    cfg = get_config(db)
    if (cfg['applications_dline'] <= time.time()):
        flasher('Application deadline has passed!', color='danger')
        return redirect(url_for('hacker.application'))

    try:
        # checkboxes
        cb_gdpr         = 'gdpr' in request.form and request.form['gdpr'] == 'on'
        cb_mlh_coc      = 'mlh_coc' in request.form and request.form['mlh_coc'] == 'on'
        cb_adult        = 'adult' in request.form and request.form['adult'] == 'on'
        cb_hackuk_admin = 'hackuk_admin' in request.form and request.form['hackuk_admin'] == 'on'
        cb_hackuk_email = 'hackuk_email' in request.form and request.form['hackuk_email'] == 'on'

        dd_gradYear = request.form['gradYear'] if 'gradYear' in request.form else None
        dd_shirt_size = request.form['shirt_size'] if 'shirt_size' in request.form else None

        c.execute('''
            UPDATE Applicants
                SET first_name=?,
                    last_name=?,
                    contact_email=?,
                    school=?,
                    gradYear=?,
                    shirt_size=?,
                    address_line_1=?,
                    address_line_2=?,
                    address_line_3=?,
                    address_city=?,
                    address_region=?,
                    address_country=?,
                    address_pcode=?,
                    description=?,
                    essay=?,
                    gdpr=?,
                    mlh_coc=?,
                    adult=?,
                    hackuk_admin=?,
                    hackuk_email=?
                WHERE
                    email=?
        ''',[
            request.form['first_name'],
            request.form['last_name'],
            request.form['contact_email'],
            request.form['school'],
            dd_gradYear,
            dd_shirt_size,
            request.form['address_line_1'],
            request.form['address_line_2'],
            request.form['address_line_3'],
            request.form['address_city'],
            request.form['address_region'],
            request.form['address_country'],
            request.form['address_pcode'],
            request.form['description'],
            request.form['essay'],
            cb_gdpr,
            cb_mlh_coc,
            cb_adult,
            cb_hackuk_admin,
            cb_hackuk_email,
            session['email']
        ])
        c.connection.commit()

        flasher('Saved successfully!', color='success')
    except Exception as e:
        raise
        print(e)
        flasher('Something went wrong! Please contact tech@hacktheburgh.com.', color='danger')

    return redirect(url_for('hacker.application'))


@bp.route('/status')
@hacker_login_required
def status():
    appl, appl_text = resolve_application(session['email'])

    if appl['completed']:
        completed_time = arrow.get(appl['completed_time']).format('MMM D, YYYY hh:mm a')
    else:
        completed_time = ''

    return render_template(
        'hacker/status.html',
        appl=appl_text,
        completed_time=completed_time,
        login_type=capitalize_login_provider()
    )

@bp.route('/invites')
@hacker_login_required
def invites():
    appl, appl_text = resolve_application(session['email'])

    if appl['completed']:
        completed_time = arrow.get(appl['completed_time']).format('MMM D, YYYY hh:mm a')
    else:
        completed_time = ''

    return render_template(
        'hacker/invites.html',
        appl=appl_text,
        completed_time=completed_time,
        login_type=capitalize_login_provider()
    )
