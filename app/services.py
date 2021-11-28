from flask import (
    Blueprint,
    request,
    redirect,
    session,
)

from .auth import admin_login_required
from .common import flasher
from .db import get_db
from uuid import uuid4
import time
import bcrypt
import arrow

"""Routes for managing services."""
bp = Blueprint("services", __name__, url_prefix="/action")


@bp.route("/service/create", methods=["POST"])
@admin_login_required
def service_create():
    """Create a service"""
    c = get_db().cursor()

    api_key = "".join(str(uuid4()).split("-"))
    api_secret = "".join((str(uuid4()) + str(uuid4())).split("-"))
    api_secret_crypt = bcrypt.hashpw(
        api_secret.encode("ascii"), bcrypt.gensalt())

    c.execute(
        """
        INSERT INTO Services (
            display_name,
            api_key,
            api_secret,
            author_email,
            active,
            created
        ) VALUES (?,?,?,?,1,?)
    """,
        [
            request.form["display_name"],
            api_key,
            api_secret_crypt,
            session["email"],
            time.time(),
        ],
    )

    c.connection.commit()

    flasher(
        f"Service <code>{request.form['display_name']}</code> added successfully.<br/>API secret: <code>{api_secret}</code>. Copy it down, it will not show again!",
        color="success",
    )

    return redirect(url_for("dashboard.list_services"))


@bp.route("/service/toggle/<api_key>")
@admin_login_required
def service_toggle(api_key):
    c = get_db().cursor()

    c.execute(
        """
        SELECT * FROM Services WHERE api_key=?
    """,
        (api_key,),
    )

    svc = c.fetchone()
    if svc is None:
        flasher(f"No such service <code>{api_key}</code>", color="warning")
        return redirect(url_for("dashboard.list_services"))

    c.execute(
        """
        UPDATE Services
            SET active=?
            WHERE api_key=?
    """,
        [1 if svc["active"] == 0 else 0, api_key],
    )

    c.connection.commit()

    flasher(f"Service {svc['display_name']} toggled.", color="success")

    return redirect(url_for("dashboard.list_services"))


@bp.route("/service/recreate_key", methods=["POST"])
@admin_login_required
def service_recreate_key():
    # check for verification string
    if request.form["verification"] != "i know what i am doing":
        flasher("Verification failed, please try again.", color="warning")
        return redirect(url_for("dashboard.list_services"))

    c = get_db().cursor()

    c.execute(
        """
        SELECT * FROM Services WHERE api_key=?
    """,
        (request.form["api_key"],),
    )

    svc = c.fetchone()
    if svc is None:
        flasher(
            f"No such service <code>{request.form['api_key']}</code>", color="warning"
        )
        return redirect(url_for("dashboard.list_services"))

    api_secret = "".join((str(uuid4()) + str(uuid4())).split("-"))
    api_secret_crypt = bcrypt.hashpw(
        api_secret.encode("ascii"), bcrypt.gensalt())

    c.execute(
        """
        UPDATE Services
            SET api_secret=?
            WHERE api_key=?
    """,
        [api_secret_crypt, request.form["api_key"]],
    )

    c.connection.commit()

    flasher(
        f"Service <code>{svc['display_name']}</code> re-keyed successfully.<br/>API secret: <code>{api_secret}</code>. Copy it down, it will not show again!",
        color="success",
    )

    return redirect(url_for("dashboard.list_services"))


@bp.route("/services/delete", methods=["POST"])
@admin_login_required
def service_delete():
    # check for verification string
    if request.form["verification"] != "i know what i am doing":
        flasher("Verification failed, please try again.", color="warning")
        return redirect(url_for("dashboard.list_services"))

    c = get_db().cursor()

    c.execute(
        """
        SELECT * FROM Services WHERE api_key=?
    """,
        (request.form["api_key"],),
    )

    svc = c.fetchone()
    if svc is None:
        flasher(
            f"No such service <code>{request.form['api_key']}</code>", color="warning"
        )
        return redirect(url_for("dashboard.list_services"))

    c.execute(
        """
        DELETE FROM Services WHERE api_key=?
    """,
        (request.form["api_key"],),
    )

    c.connection.commit()

    flasher(
        f"Service <code>{svc['display_name']}</code> deleted successfully.",
        color="success",
    )

    return redirect(url_for("dashboard.list_services"))
