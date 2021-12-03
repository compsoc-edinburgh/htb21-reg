from flask import (
    Blueprint,
    flash,
    request,
    redirect,
    url_for,
    send_file,
    current_app,
    session,
    Response,
)

from .auth import admin_login_required
from .common import flasher
from .data import get_applicants_from_csv, insert_applicant, create_csv
from .db import get_db
from uuid import uuid4
import time
import bcrypt
import arrow
import functools

bp = Blueprint("actions", __name__, url_prefix="/action")


def verification_required(view):
    """View decorator that checks POST['verification'] == "i know what i am doing" """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        # check for verification string
        if request.form["verification"] != "i know what i am doing":
            flasher("Verification failed, please try again.", color="warning")
            return redirect(url_for("dashboard.admin"))
        return view()

    return wrapped_view


@bp.route("/update_cfg", methods=["POST"])
@admin_login_required
def update_cfg():
    """Update site config, for example application window and event start dates."""
    c = get_db().cursor()

    c.execute(
        """
        UPDATE Configuration
            SET applications_open=?,
                applications_dline=?,
                event_start=?
            WHERE
                id=0
    """,
        [
            arrow.get(request.form["applications_open"]).timestamp(),
            arrow.get(request.form["applications_dline"]).timestamp(),
            arrow.get(request.form["event_start"]).timestamp(),
        ],
    )

    c.connection.commit()

    flasher("Event configuration updated.", color="success")

    return redirect(url_for("dashboard.edit_config"))


@bp.route("/download_csv/export.csv")
@admin_login_required
def download_csv():
    """Download all applicants as a CSV"""
    conn = get_db()
    csv_str = create_csv(conn, request.args.get('sensitive') is not None)
    return Response(csv_str, mimetype="text/csv")


@bp.route("/votes/purge", methods=["POST"])
@admin_login_required
@verification_required
def purge_votes():
    """Purge all votes from the database"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM Votes")

    conn.commit()
    flasher("Purged {} votes.".format(c.rowcount), color="success")
    return redirect(url_for("dashboard.admin"))


@bp.route("/vote/submit", methods=["POST"])
@admin_login_required
def submit_vote():
    """Submit a vote"""
    if not "rating" in request.form:
        flasher("Please select a rating!", color="danger")
        return redirect(
            url_for("dashboard.applicant",
                    user_id=request.form["user_id"]) + "?flow=1"
        )

    flow_voting = request.args.get("flow") is not None

    print(
        "voting: {} {} -> {} {}".format(
            session["name"],
            session["email"],
            request.form["user_id"],
            request.form["rating"],
        )
    )

    # find previous vote if it exists
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM Votes WHERE app_id=? AND author_email=?",
        (request.form["user_id"], session["email"]),
    )

    previousVote = c.fetchone()

    if previousVote is None:
        print("previous vote does not exist")
        c.execute(
            """
            INSERT INTO Votes (rating, author, author_email, app_id) VALUES (?, ?, ?, ?)""",
            (
                request.form["rating"],
                session["name"],
                session["email"],
                request.form["user_id"],
            ),
        )
        if not flow_voting:
            flasher("Vote recorded successfully!", color="success")
    else:
        print("previous vote exists")
        c.execute(
            """
            UPDATE Votes
            SET rating=? WHERE app_id=? AND author_email=?
        """,
            (request.form["rating"],
             request.form["user_id"], session["email"]),
        )
        flasher("Vote updated successfully!", color="success")

    conn.commit()

    if flow_voting:
        return redirect(url_for("dashboard.get_next_applicant"))
    else:
        return redirect(url_for("dashboard.applicant", user_id=request.form["user_id"]))


@bp.route("/toggle_hiding")
@admin_login_required
def toggle_hiding():
    """Toggle name redaction for the current user."""
    if not "redacted" in session:
        session["redacted"] = True
    else:
        session["redacted"] = not session["redacted"]

    return redirect(url_for("dashboard.rate_queue"))


@bp.route("/invites/new", methods=["POST"])
@admin_login_required
def invite_create():
    """Add an invite for a given user."""
    link = request.form["link"] if "link" in request.form else None
    code = request.form["code"] if "code" in request.form else None

    c = get_db().cursor()
    c.execute(
        """
        INSERT INTO Invites (app_id, service, link, code)
        VALUES (?,?,?,?)
    """,
        [request.form["app_id"], request.form["service"], link, code],
    )

    c.connection.commit()

    flasher("Created invite successfully!", color="success")

    return redirect(url_for("dashboard.list_invites"))


@bp.route("/invites/delete/<inv_id>")
@admin_login_required
def invite_delete(inv_id):
    """Delete a given invite"""
    c = get_db().cursor()
    c.execute(
        """
        DELETE FROM Invites WHERE id=?
    """,
        [inv_id],
    )

    c.connection.commit()

    flasher("Deleted invite successfully!", color="success")

    return redirect(url_for("dashboard.list_invites"))
