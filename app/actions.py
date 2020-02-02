from flask import Blueprint, flash, request, redirect, url_for

from .auth import login_required
from .common import flasher
from .data import get_applicants_from_csv, insert_applicant
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
