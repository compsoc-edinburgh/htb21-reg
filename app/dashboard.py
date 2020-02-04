from flask import Blueprint, session, render_template, request, flash, redirect, url_for, escape
import functools
import arrow
from .auth import login_required
from .db import get_db
from .common import flasher

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
@login_required
def index():
    #return 'hello, ' + session['email']
    return render_template('dashboard/index.html', session=session)

@bp.route('/admin')
@login_required
def admin():
    return render_template('dashboard/admin.html', session=session)

@bp.route('/table')
@login_required
def table():
    # parse query params
    sort = request.args.get('sort')
    reverse = request.args.get('reverse') is not None
    sorts_available=['mongo_id', 'verified', 'completed', 'name', 'email', 'school']
    if sort is None or (not sort in sorts_available):
        sort = 'mongo_id'

    # retreive from db
    c = get_db().cursor()

    # OK SO THIS LOOKS REALLY BAD BUT
    # we have already vetted our sort as explicitly part of a small number of columns, and SQLite does not let us interpolate the field name
    c.execute('''
        SELECT * FROM Applicants ORDER BY {} {}
    '''.format(sort, 'DESC' if reverse else 'ASC'))
    applicants = c.fetchall()

    out = []
    for applicant in applicants:
        applicant = dict(applicant)
        c.execute('''
            SELECT
                COUNT(app_id), AVG(rating)
            FROM Votes
            WHERE
                app_id=?
        ''', (applicant['mongo_id'],))
        
        row = c.fetchone()
        applicant['ratings'] = row[0]
        if row[1] is not None:
            applicant['score'] = '{:.3}'.format(row[1])
        else:
            applicant['score'] = ''
        out.append(applicant)

    # hack, but we need to be able to sort by these virtual fields too
    sort = request.args.get('sort')
    if sort == 'ratings' or sort == 'score':
        out.sort(key=lambda k: k[sort])
        if reverse:
            out.reverse()

    return render_template(
        'dashboard/table.html',
        session=session,
        rows=out,
        sort=sort,
        sort_reverse=reverse
    )

@bp.route('/applicant/<mongo_id>')
@login_required
def applicant(mongo_id):
    c = get_db().cursor()
    
    c.execute('SELECT * FROM Applicants WHERE mongo_id = ?', (mongo_id,))

    row = c.fetchone()
    if row is None:
        flasher('No such user with ID {}!'.format(mongo_id), color='danger')
        return redirect(url_for('dashboard.table'))

    # make sure newlines work
    essay       = str(escape(row['essay'])).replace('\\n', '<br/>')
    description = str(escape(row['description'])).replace('\\n', '<br/>')

    # required to divide by 1000 bc timestamp is milliseconds from epoch
    # versus seconds
    # ... fucking hell
    timestamp = arrow.get(int(row['timestamp']) / 1000).format('YYYY-MM-DD HH:mm:ss')

    # resolve vote
    c.execute(
        'SELECT rating FROM Votes WHERE app_id=? AND author_email=?',
        (row['mongo_id'], session['email'])
    )
    previousVote = c.fetchone()
    if previousVote is not None:
        previousVote = { 'value': previousVote['rating'] }

    c.execute('SELECT author, author_email, rating FROM Votes WHERE app_id=?', (row['mongo_id'],))
    votes = c.fetchall()
    print(votes)

    votes += [
            {'rating': 5, 'author_email': 'user1@long.domain.com', 'author': 'John Doe' },
            {'rating': 4, 'author_email': 'user2@long.domain.com', 'author': 'John Doe' },
            {'rating': 4, 'author_email': 'longlonglonglonglong@long.domain.com', 'author': 'John Doe' },
            {'rating': 3, 'author_email': 'user4@long.domain.com', 'author': 'John Doe' },
            {'rating': 2, 'author_email': 'user5@long.domain.com', 'author': 'John Doe' },
            {'rating': 3, 'author_email': 'user6@long.domain.com', 'author': 'John Doe' },
            {'rating': 1, 'author_email': 'user7@long.domain.com', 'author': 'John Doe' }
    ]

    voteaverage = functools.reduce( lambda a,v: a + v['rating'], votes, 0 ) / len(votes)
    voteaverage = '{:.3}'.format(voteaverage)

    return render_template(
        'dashboard/applicant.html',
        session=session,
        applicant=row,
        timestamp=timestamp,
        essay=essay,
        description=description,
        previousVote=previousVote,
        votes=votes,
        voteaverage=voteaverage
    )
