from flask import Blueprint, flash, request, redirect, url_for, send_file, current_app, session, Response

from .auth import admin_login_required
from .common import flasher
from .data import get_applicants_from_csv, insert_applicant, create_csv
from .db import get_db
from uuid import uuid4
import time
import bcrypt
import arrow

bp = Blueprint('actions', __name__, url_prefix='/action')

@bp.route('/update_cfg', methods=['POST'])
@admin_login_required
def update_cfg():
    c = get_db().cursor()

    c.execute('''
        UPDATE Configuration
            SET applications_open=?,
                applications_dline=?,
                event_start=?
            WHERE
                id=0
    ''', [
        arrow.get(request.form['applications_open']).timestamp(),
        arrow.get(request.form['applications_dline']).timestamp(),
        arrow.get(request.form['event_start']).timestamp(),
    ])

    c.connection.commit()

    flasher('Event configuration updated.', color='success')

    return redirect(url_for('dashboard.edit_config'))

@bp.route('/submit_dump', methods=['POST'])
@admin_login_required
def submit_dump():

    # check for verification string
    if request.form['verification'] != 'i know what i am doing':
        flasher('Verification failed, please try again.', color='warning')
        return redirect(url_for('dashboard.admin'))

    # import all applicants
    conn = get_db()
    cursor = conn.cursor()
    count = 0
    for applicant in get_applicants_from_csv(request.files['csv']):
        insert_applicant(cursor, applicant)
        count += 1
    conn.commit()
    flasher('Imported {} records.'.format(count), color='success')

    return redirect(url_for('dashboard.admin'))

@bp.route('/votes/purge', methods=['POST'])
@admin_login_required
def purge_votes():
    # check for verification string
    if request.form['verification'] != 'i know what i am doing':
        flasher('Verification failed, please try again.', color='warning')
        return redirect(url_for('dashboard.admin'))

    # import all applicants
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM Votes')

    conn.commit()
    flasher('Purged {} votes.'.format(c.rowcount), color='success')
    return redirect(url_for('dashboard.admin'))
    

@bp.route('/download_db/registrations.sqlite')
@admin_login_required
def download_db():
    return send_file(current_app.config['DATABASE'])

@bp.route('/vote/submit', methods=['POST'])
@admin_login_required
def submit_vote():
    if not 'rating' in request.form:
        flasher('Please select a rating!', color='danger')
        return redirect(url_for('dashboard.applicant', user_id=request.form['user_id']) + '?flow=1')


    flow_voting = request.args.get('flow') is not None

    print('voting: {} {} -> {} {}'.format(session['name'], session['email'], request.form['user_id'], request.form['rating']))

    # find previous vote if it exists
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM Votes WHERE app_id=? AND author_email=?', 
        (request.form['user_id'], session['email'])
    )

    previousVote = c.fetchone()

    if previousVote is None:
        print('previous vote does not exist')
        c.execute('''
            INSERT INTO Votes (rating, author, author_email, app_id) VALUES (?, ?, ?, ?)''',
            (request.form['rating'], session['name'], session['email'], request.form['user_id'])
        )
        if not flow_voting:
            flasher('Vote recorded successfully!', color='success')
    else:
        print('previous vote exists')
        c.execute('''
            UPDATE Votes
            SET rating=? WHERE app_id=? AND author_email=?
        ''', (request.form['rating'], request.form['user_id'], session['email'])
        )
        flasher('Vote updated successfully!', color='success')

    conn.commit()


    if flow_voting:
        return redirect(url_for('dashboard.get_next_applicant'))
    else:
        return redirect(url_for('dashboard.applicant', user_id=request.form['user_id']))

@bp.route('/download_csv/export.csv')
@admin_login_required
def download_csv():
    conn = get_db()
    csv_str = create_csv(conn)
    return Response(
        csv_str,
        mimetype='text/csv'
    )

@bp.route('/toggle_hiding')
@admin_login_required
def toggle_hiding():
    if not 'redacted' in session:
        session['redacted'] = True
    else:
        session['redacted'] = not session['redacted']

    return redirect(url_for('dashboard.rate_queue'))

# service actions

@bp.route('/service/create', methods=['POST'])
@admin_login_required
def service_create():
    c = get_db().cursor()

    api_key = ''.join(str(uuid4()).split('-'))
    api_secret = ''.join((str(uuid4()) + str(uuid4())).split('-'))
    api_secret_crypt = bcrypt.hashpw(api_secret.encode('ascii'), bcrypt.gensalt())

    c.execute('''
        INSERT INTO Services (
            display_name,
            api_key,
            api_secret,
            author_email,
            active,
            created
        ) VALUES (?,?,?,?,1,?)
    ''', [
        request.form['display_name'],
        api_key,
        api_secret_crypt,
        session['email'],
        time.time()
    ])

    c.connection.commit()

    flasher(f"Service <code>{request.form['display_name']}</code> added successfully.<br/>API secret: <code>{api_secret}</code>. Copy it down, it will not show again!", color="success")

    return redirect(url_for('dashboard.list_services'))

@bp.route('/service/toggle/<api_key>')
@admin_login_required
def service_toggle(api_key):
    c = get_db().cursor()

    c.execute('''
        SELECT * FROM Services WHERE api_key=?
    ''', (api_key,))

    svc = c.fetchone()
    if svc is None:
        flasher(f'No such service <code>{api_key}</code>', color='warning')
        return redirect(url_for('dashboard.list_services'))

    c.execute('''
        UPDATE Services
            SET active=?
            WHERE api_key=?
    ''', [
        1 if svc['active'] == 0 else 0,
        api_key
    ])

    c.connection.commit()

    flasher(f"Service {svc['display_name']} toggled.", color='success')

    return redirect(url_for('dashboard.list_services'))

@bp.route('/service/recreate_key', methods=['POST'])
@admin_login_required
def service_recreate_key():
    # check for verification string
    if request.form['verification'] != 'i know what i am doing':
        flasher('Verification failed, please try again.', color='warning')
        return redirect(url_for('dashboard.list_services'))

    c = get_db().cursor()

    c.execute('''
        SELECT * FROM Services WHERE api_key=?
    ''', (request.form['api_key'],))

    svc = c.fetchone()
    if svc is None:
        flasher(f"No such service <code>{request.form['api_key']}</code>", color='warning')
        return redirect(url_for('dashboard.list_services'))

    api_secret = ''.join((str(uuid4()) + str(uuid4())).split('-'))
    api_secret_crypt = bcrypt.hashpw(api_secret.encode('ascii'), bcrypt.gensalt())

    c.execute('''
        UPDATE Services
            SET api_secret=?
            WHERE api_key=?
    ''', [
        api_secret_crypt,
        request.form['api_key']
    ])

    c.connection.commit()

    flasher(f"Service <code>{svc['display_name']}</code> re-keyed successfully.<br/>API secret: <code>{api_secret}</code>. Copy it down, it will not show again!", color="success")
    
    return redirect(url_for('dashboard.list_services'))

@bp.route('/services/delete', methods=['POST'])
@admin_login_required
def service_delete():
    # check for verification string
    if request.form['verification'] != 'i know what i am doing':
        flasher('Verification failed, please try again.', color='warning')
        return redirect(url_for('dashboard.list_services'))

    c = get_db().cursor()

    c.execute('''
        SELECT * FROM Services WHERE api_key=?
    ''', (request.form['api_key'],))

    svc = c.fetchone()
    if svc is None:
        flasher(f"No such service <code>{request.form['api_key']}</code>", color='warning')
        return redirect(url_for('dashboard.list_services'))

    c.execute('''
        DELETE FROM Services WHERE api_key=?
    ''', (request.form['api_key'],)
    )

    c.connection.commit()

    flasher(f"Service <code>{svc['display_name']}</code> deleted successfully.", color='success')

    return redirect(url_for('dashboard.list_services'))


@bp.route('/invites/new', methods=['POST'])
@admin_login_required
def invite_create():
    
    link = request.form['link'] if 'link' in request.form else None
    code = request.form['code'] if 'code' in request.form else None

    c = get_db().cursor()
    c.execute('''
        INSERT INTO Invites (app_id, service, link, code)
        VALUES (?,?,?,?)
    ''', [
        request.form['app_id'],
        request.form['service'],
        link,
        code
    ])
    
    c.connection.commit()

    flasher('Created invite successfully!', color='success')

    return redirect(url_for('dashboard.list_invites'))


@bp.route('/invites/delete/<inv_id>')
@admin_login_required
def invite_delete(inv_id):
    c = get_db().cursor()
    c.execute('''
        DELETE FROM Invites WHERE id=?
    ''', [inv_id])

    c.connection.commit()

    flasher('Deleted invite successfully!', color='success')

    return redirect(url_for('dashboard.list_invites'))
