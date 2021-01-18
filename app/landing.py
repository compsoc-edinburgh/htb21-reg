from flask import Blueprint, render_template
from .common import get_config
from .db import get_db
import arrow
import time

bp = Blueprint('landing', __name__)

@bp.route('/')
def index():
    cfg = get_config(get_db())
    now = time.time()
    if now <= cfg['applications_dline']:
        closein = arrow.get(cfg['applications_dline']).humanize(granularity=['day', 'hour'])
        status = f'Registrations close {closein}.'
    else:
        status = 'Registrations are closed!'

    return render_template('index.html', status=status)
