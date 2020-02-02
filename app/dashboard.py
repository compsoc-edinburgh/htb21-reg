from flask import Blueprint, session, render_template
from .auth import login_required

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
