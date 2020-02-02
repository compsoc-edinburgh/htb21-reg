from flask import Blueprint, session, render_template, request, flash
from .auth import login_required
from .db import get_db

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
def table():
    # parse query params
    sort = request.args.get('sort')
    reverse = request.args.get('reverse') is not None
    sorts_available=['mongo_id', 'verified', 'completed', 'name', 'email', 'school']
    if sort is None or (not sort in sorts_available):
        sort = 'mongo_id'
    print('sort', sort, 'reverse', reverse)

    # retreive from db
    c = get_db().cursor()

    # OK SO THIS LOOKS REALLY BAD BUT
    # we have already vetted our sort as explicitly part of a small number of columns, and SQLite does not let us interpolate the field name
    c.execute('SELECT * FROM Applicants ORDER BY {} {}'.format(sort, 'DESC' if reverse else 'ASC'))
    
    return render_template(
        'dashboard/table.html',
        session=session,
        rows=c.fetchall(),
        sort=sort,
        sort_reverse=reverse
    )
