from flask import Blueprint, render_template, session
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
        closein = arrow.get(cfg['applications_dline']).humanize(
            granularity=['day', 'hour'])
        status = f'Registrations close {closein}.'
    else:
        status = 'Registrations are closed!'

    return render_template('index.html', status=status)


@bp.route('/discord')
def discord_landing():
    session['post_login_redirect'] = 'hacker.discord'
    return render_template('discord.html')


@bp.route('/phone')
def phone_landing():
    session['post_login_redirect'] = 'hacker.phone'
    return render_template('phone.html')
