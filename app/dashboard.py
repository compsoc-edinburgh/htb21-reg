from flask import (
    Blueprint,
    session,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    escape,
)
import functools
import arrow
from markdown import markdown
from .auth import admin_login_required
from .db import get_db
from .common import flasher, get_config

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("/")
@admin_login_required
def index():
    """Index dashboard"""
    # TODO: Some sort of caching?

    metrics = {"applicants": {}, "votes": {}}
    conn = get_db()
    c = conn.cursor()

    # get the applicant metrics
    c.execute("SELECT COUNT(id) FROM Applicants")
    metrics["applicants"]["all"] = c.fetchone()[0]
    c.execute("SELECT COUNT(id) FROM Applicants WHERE verified=1")
    metrics["applicants"]["verified"] = c.fetchone()[0]
    c.execute("SELECT COUNT(id) FROM Applicants WHERE completed=1")
    metrics["applicants"]["completed"] = c.fetchone()[0]

    # get vote metrics
    c.execute("SELECT COUNT(id) FROM Votes")
    metrics["votes"]["all"] = c.fetchone()[0]
    c.execute("SELECT COUNT(id) FROM Votes WHERE rating=1")
    metrics["votes"]["1"] = c.fetchone()[0]
    c.execute("SELECT COUNT(id) FROM Votes WHERE rating=2")
    metrics["votes"]["2"] = c.fetchone()[0]
    c.execute("SELECT COUNT(id) FROM Votes WHERE rating=3")
    metrics["votes"]["3"] = c.fetchone()[0]
    c.execute("SELECT COUNT(id) FROM Votes WHERE rating=4")
    metrics["votes"]["4"] = c.fetchone()[0]
    c.execute("SELECT COUNT(id) FROM Votes WHERE rating=5")
    metrics["votes"]["5"] = c.fetchone()[0]
    c.execute("SELECT DISTINCT author, author_email FROM Votes")
    author_names = c.fetchall()
    authors = []
    if author_names is None:
        author_names = []
    for author in author_names:
        c.execute(
            "SELECT COUNT(id), AVG(rating) FROM Votes WHERE author_email=?",
            (author["author_email"],),
        )
        row = c.fetchone()
        authors.append(
            {
                "name": author["author"],
                "email": author["author_email"],
                "count": row[0],
                "average": "{:.2}".format(row[1]),
            }
        )

    authors.sort(key=lambda a: a["count"])
    if authors is not None:
        authors.reverse()
    metrics["votes"]["authors"] = authors

    return render_template("dashboard/index.html", session=session, metrics=metrics)


@bp.route("/admin")
@admin_login_required
def admin():
    return render_template("dashboard/admin.html", session=session)


@bp.route("/table")
@admin_login_required
def table():
    # parse query params
    sort = request.args.get("sort")
    reverse = request.args.get("reverse") is not None
    SORTS_AVAILABLE = ["user_id", "verified",
                       "completed", "name", "email", "school"]
    if sort is None or (sort not in SORTS_AVAILABLE):
        sort = "user_id"

    # retreive from db
    c = get_db().cursor()

    # OK SO THIS LOOKS REALLY BAD BUT
    # we have already vetted our sort as explicitly part of a small number of columns, and SQLite does not let us interpolate the field name
    c.execute(
        """
        SELECT * FROM Applicants ORDER BY {} {}
    """.format(
            sort, "DESC" if reverse else "ASC"
        )
    )
    applicants = c.fetchall()

    out = []
    for applicant in applicants:
        applicant = dict(applicant)
        c.execute(
            """
            SELECT
                COUNT(app_id), AVG(rating)
            FROM Votes
            WHERE
                app_id=?
        """,
            (applicant["user_id"],),
        )

        row = c.fetchone()
        applicant["ratings"] = row[0]
        if row[1] is not None:
            applicant["score"] = "{:.3}".format(row[1])
        else:
            applicant["score"] = ""
        out.append(applicant)

    # hack, but we need to be able to sort by these virtual fields too
    sort = request.args.get("sort")
    if sort == "ratings" or sort == "score":
        out.sort(key=lambda k: k[sort])
        if reverse:
            out.reverse()

    return render_template(
        "dashboard/table.html",
        session=session,
        rows=out,
        sort=sort,
        sort_reverse=reverse,
    )


@bp.route("/applicant/<user_id>")
@admin_login_required
def applicant(user_id):
    c = get_db().cursor()

    c.execute("SELECT * FROM Applicants WHERE user_id = ?", (user_id,))

    row = c.fetchone()
    if row is None:
        flasher("No such user with ID {}!".format(user_id), color="danger")
        return redirect(url_for("dashboard.table"))

    # make sure newlines work
    essay = str(escape(row["essay"])).replace("\\n", "<br/>")
    description = str(escape(row["description"])).replace("\\n", "<br/>")

    # required to divide by 1000 bc timestamp is milliseconds from epoch
    # versus seconds
    # ... fucking hell
    timestamp = arrow.get(int(row["timestamp"]) /
                          1000).format("YYYY-MM-DD HH:mm:ss")

    # resolve vote
    c.execute(
        "SELECT rating FROM Votes WHERE app_id=? AND author_email=?",
        (row["user_id"], session["email"]),
    )
    previousVote = c.fetchone()
    if previousVote is not None:
        previousVote = {"value": previousVote["rating"]}

    c.execute(
        "SELECT author, author_email, rating FROM Votes WHERE app_id=?",
        (row["user_id"],),
    )
    votes = c.fetchall()

    if len(votes) != 0:
        voteaverage = functools.reduce(lambda a, v: a + v["rating"], votes, 0) / len(
            votes
        )
        voteaverage = "{:.3}".format(voteaverage)
    else:
        voteaverage = "?"

    c.execute(
        """
        SELECT COUNT(a.id) FROM Applicants a
        INNER JOIN Votes v ON a.user_id = v.app_id
        WHERE
            v.author_email = ? AND a.completed=1
    """,
        (session["email"],),
    )
    flow_votes_completed = c.fetchone()[0]
    c.execute(
        """
        SELECT COUNT(a.id) FROM Applicants a
        WHERE
            a.completed=1
    """
    )
    flow_votes_total = c.fetchone()[0]

    if flow_votes_total > 0:
        flow_votes_percentage = "{:0.2f}".format(
            100 * (flow_votes_completed / flow_votes_total)
        )
    else:
        flow_votes_percentage = "0.00%"

    applicant_txt = ""
    for key in row.keys():
        applicant_txt += f"{key}: {row[key]}\n"

    return render_template(
        "dashboard/applicant.html",
        session=session,
        applicant=row,
        applicant_txt=applicant_txt,
        timestamp=timestamp,
        essay=essay,
        description=description,
        previousVote=previousVote,
        votes=votes,
        voteaverage=voteaverage,
        flow=request.args.get("flow"),
        flow_votes_completed=flow_votes_completed,
        flow_votes_total=flow_votes_total,
        flow_votes_percentage=flow_votes_percentage,
    )


@bp.route("/rate_queue")
@admin_login_required
def rate_queue():
    conn = get_db()

    # this should be cleaner but won't be
    c = conn.cursor()
    c.execute(
        """
        SELECT first_name, last_name, email, user_id
        FROM
            Applicants
        WHERE
            completed=1
        ORDER BY email ASC
    """
    )

    rows = c.fetchall()
    targets = []
    done = []
    for row in rows:
        c.execute(
            """
            SELECT COUNT(app_id) FROM Votes
            WHERE
                app_id=? AND author_email=?
        """,
            (row["user_id"], session["email"]),
        )
        vcount = c.fetchone()

        if vcount[0] == 0:
            targets.append(
                {
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "user_id": row["user_id"],
                }
            )
        else:
            done.append(
                {
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "user_id": row["user_id"],
                }
            )

    return render_template(
        "dashboard/rate_queue.html", session=session, targets=targets, done=done
    )


@bp.route("/rate_next")
@admin_login_required
def get_next_applicant():
    # next applicant algorithm:
    # find the next applicant that you haven't yet voted on, and has the least amount of votes

    conn = get_db()
    c = conn.cursor()

    c = conn.cursor()
    c.execute(
        """
        SELECT user_id, email
        FROM
            Applicants
        WHERE
            completed=1
        ORDER BY email ASC
    """
    )
    rows = c.fetchall()

    targets = []
    for row in rows:
        c.execute(
            """
            SELECT COUNT(app_id)
            FROM Votes
            WHERE
                app_id=? AND author_email=?
        """,
            (row["user_id"], session["email"]),
        )
        if c.fetchone()[0] != 0:
            # we've already voted
            continue

        # figure out how many votes are here
        c.execute(
            """
            SELECT
                COUNT(app_id)
            FROM Votes WHERE
                app_id=?
        """,
            (row["user_id"],),
        )
        count = c.fetchone()[0]
        targets.append({"user_id": row["user_id"], "count": count})

    if len(targets) != 0:
        targets.sort(key=lambda k: k["count"])
        return redirect(
            url_for("dashboard.applicant",
                    user_id=targets[0]["user_id"]) + "?flow=1"
        )
    else:
        flasher("Congrats! You've finished!", color="success")
        return redirect(url_for("dashboard.rate_queue"))


@bp.route("/export")
@admin_login_required
def export_csv():
    return render_template("dashboard/export.html", session=session)


@bp.route("/services")
@admin_login_required
def list_services():
    c = get_db().cursor()
    c.execute(
        """
        SELECT api_key, display_name, author_email, created, last_used, active
        FROM Services
    """
    )
    services = c.fetchall()

    svcs = []
    for svc_row in services:
        svc = {}
        for key in svc_row.keys():
            svc[key] = svc_row[key]

        svc["created"] = arrow.get(
            svc["created"]).format("YYYY-MM-DD HH:mm:ss")
        if svc["last_used"] is not None:
            svc["last_used"] = arrow.get(
                svc["last_used"]).format("YYYY-MM-DD HH:mm:ss")

        svcs.append(svc)

    return render_template("dashboard/services.html", session=session, services=svcs)


@bp.route("/services/docs")
@admin_login_required
def services_docs():
    from .services import api_routes

    endpoints = []
    for func in api_routes:
        if func.__doc__:
            doc = func.__doc__.split("\n")
            doc = [(line[3:] if len(line) > 3 else line) for line in doc]
            doc = "\n".join(doc)
            doc = markdown(doc)
        else:
            doc = ""
        ep = {
            "name": func.__name__,
            "doc": doc,
            "url": url_for(f"service_api.{func.__name__}"),
        }
        endpoints.append(ep)

    return render_template(
        "dashboard/services_doc.html", session=session, endpoints=endpoints
    )


@bp.route("/config")
@admin_login_required
def edit_config():
    db = get_db()
    cfg = get_config(db)

    strtimes = {
        "applications_open": arrow.get(cfg["applications_open"]).format(),
        "applications_dline": arrow.get(cfg["applications_dline"]).format(),
        "event_start": arrow.get(cfg["event_start"]).format(),
    }

    return render_template(
        "dashboard/config.html", session=session, config=cfg, strtimes=strtimes
    )


@bp.route("/invites")
@admin_login_required
def list_invites():
    c = get_db().cursor()

    c.execute(
        """
        SELECT i.id, i.app_id, i.service, i.code, i.link, a.email
            FROM Invites i
            LEFT JOIN Applicants a ON a.user_id=i.app_id
    """
    )

    rows = c.fetchall()

    if rows is None:
        rows = []

    return render_template("dashboard/invites.html", session=session, invites=rows)


@bp.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response
