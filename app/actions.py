from flask import Blueprint, flash, request, redirect, url_for, send_file, current_app, session

from .auth import login_required
from .common import flasher
from .data import get_applicants_from_csv, insert_applicant, create_csv
from .db import get_db
bp = Blueprint('actions', __name__, url_prefix='/action')


@bp.route('/submit_dump', methods=['POST'])
@login_required
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
@login_required
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
    

@bp.route('/download_db/votes.sqlite')
@login_required
def download_db():
    return send_file(current_app.config['DATABASE'])

@bp.route('/vote/submit', methods=['POST'])
@login_required
def submit_vote():
    if not 'rating' in request.form:
        flasher('Please select a rating!', color='danger')
        return redirect(url_for('dashboard.applicant', mongo_id=request.form['mongo_id']) + '?flow=1')


    flow_voting = request.args.get('flow') is not None

    print('voting: {} {} -> {} {}'.format(session['name'], session['email'], request.form['mongo_id'], request.form['rating']))

    # find previous vote if it exists
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM Votes WHERE app_id=? AND author_email=?', 
        (request.form['mongo_id'], session['email'])
    )

    previousVote = c.fetchone()

    if previousVote is None:
        print('previous vote does not exist')
        c.execute('''
            INSERT INTO Votes (rating, author, author_email, app_id) VALUES (?, ?, ?, ?)''',
            (request.form['rating'], session['name'], session['email'], request.form['mongo_id'])
        )
        if not flow_voting:
            flasher('Vote recorded successfully!', color='success')
    else:
        print('previous vote exists')
        c.execute('''
            UPDATE Votes
            SET rating=? WHERE app_id=? AND author_email=?
        ''', (request.form['rating'], request.form['mongo_id'], session['email'])
        )
        flasher('Vote updated successfully!', color='success')

    conn.commit()


    if flow_voting:
        return redirect(url_for('dashboard.get_next_applicant'))
    else:
        return redirect(url_for('dashboard.applicant', mongo_id=request.form['mongo_id']))

@bp.route('/download_csv/export.csv')
@login_required
def download_csv():
    conn = get_db()
    csv_str = create_csv(conn)
    return csv_str

@bp.route('/toggle_hiding')
@login_required
def toggle_hiding():
    if not 'redacted' in session:
        session['redacted'] = True
    else:
        session['redacted'] = not session['redacted']

    return redirect(url_for('dashboard.rate_queue'))

