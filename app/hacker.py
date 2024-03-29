from flask import Blueprint, render_template, session, url_for, redirect, request, current_app
from .auth import hacker_login_required
from .common import flasher, get_config
from .db import get_db
from json import dumps
import arrow
import time
from multiprocessing import Process
import requests
import tempfile
import boto3
import shutil
import os
from wtforms import Form, StringField, EmailField, IntegerField, SelectField, BooleanField, validators

bp = Blueprint("hacker", __name__, url_prefix="/hacker")


class ApplicationForm(Form):
    first_name = StringField('First Name', [validators.Length(min=1, max=50)])
    last_name = StringField('Last Name', [validators.Length(min=1, max=50)])
    contact_email = EmailField('Email')
    school = StringField('University Name', [
                         validators.Length(min=1, max=75)])
    allergens = StringField('Dietary Requirements', [
        validators.Length(min=0, max=100)])
    gradYear = IntegerField("Graduation Year")
    shirt_size = SelectField(
        "Shirt Size", choices=[("xs", "XS"), ("s", "S"), ("m", "M"), ("l", "L"), ("xl", "XL")])
    address_line_1 = StringField(
        'Address Line 1', [validators.Length(min=1, max=75)])
    address_line_2 = StringField(
        'Address Line 2', [validators.Length(min=0, max=75)])
    address_line_3 = StringField(
        'Address Line 3', [validators.Length(min=0, max=75)])
    address_city = StringField('City', [validators.Length(min=0, max=75)])
    address_region = StringField('Region', [validators.Length(min=0, max=75)])
    address_country = StringField(
        'Country', [validators.Length(min=0, max=40)])
    address_pcode = StringField('Postcode', [validators.Length(min=0, max=10)])
    phone = StringField('Phone Number', [validators.Length(min=11, max=15)])
    description = StringField('"Why are you excited about Hack the Burgh?"', [
                              validators.Length(min=1, max=500)])
    essay = StringField('"Describe an interesting project you\'ve been involved in"', [
                        validators.Length(min=1, max=500)])
    mlh_coc = BooleanField("MLH Code of Conduct", [validators.DataRequired()])
    gdpr = BooleanField("Privacy Policy", [validators.DataRequired()])
    mlh_admin = BooleanField("MLH Privacy Policy", [validators.DataRequired()])
    hackuk_admin = BooleanField("HackUK Privacy Policy", [
                                validators.DataRequired()])
    adult = BooleanField("Over 18", [validators.DataRequired()])
    vaccinated = BooleanField("Fully Vaccinated", [validators.DataRequired()])


# Similar to above, but allows empty fields. This is used to make sure we still don't let people
# put as much data as they want
class IncompleteApplicationForm(Form):
    first_name = StringField('First Name', [validators.Length(min=0, max=50)])
    last_name = StringField('Last Name', [validators.Length(min=0, max=50)])
    contact_email = StringField('Email', [validators.Length(min=0, max=50)])
    school = StringField('University Name', [
                         validators.Length(min=0, max=75)])
    allergens = StringField('Dietary Requirements', [
        validators.Length(min=0, max=100)])
    gradYear = IntegerField("Graduation Year")
    shirt_size = SelectField(
        "Shirt Size", choices=[("", "Select"), ("xs", "XS"), ("s", "S"), ("m", "M"), ("l", "L"), ("xl", "XL")])
    address_line_1 = StringField(
        'Address Line 1', [validators.Length(min=0, max=75)])
    address_line_2 = StringField(
        'Address Line 2', [validators.Length(min=0, max=75)])
    address_line_3 = StringField(
        'Address Line 3', [validators.Length(min=0, max=75)])
    address_city = StringField('City', [validators.Length(min=0, max=75)])
    address_region = StringField('Region', [validators.Length(min=0, max=75)])
    address_country = StringField(
        'Country', [validators.Length(min=0, max=40)])
    address_pcode = StringField('Postcode', [validators.Length(min=0, max=10)])
    phone = StringField('Phone Number', [validators.Length(min=0, max=15)])
    description = StringField('"Why are you excited about Hack the Burgh?"', [
                              validators.Length(min=0, max=500)])
    essay = StringField('"Describe an interesting project you\'ve been involved in"', [
                        validators.Length(min=0, max=500)])


def capitalize_login_provider():
    if session["login_type"] == "mlh":
        return "MLH"
    elif session["login_type"] == "github":
        return "Github"


@bp.route("/import/mlh")
@hacker_login_required
def init_mlh():
    c = get_db().cursor()
    print("mlh_id: ", session["mlh_info"])
    mlh_id = session["mlh_info"]["id"]
    email = session["mlh_info"]["email"]

    school_name = (
        session["mlh_info"]["school"]["name"]
        if "name" in session["mlh_info"]["school"]
        else None
    )

    c.execute("SELECT COUNT(1) FROM Applicants WHERE email=?", (email,))
    if c.fetchone()[0] != 1:
        # first login, init profile
        c.execute(
            """
            INSERT INTO Applicants
                (verified, admin, adult, completed, admitted, user_id, email, contact_email, mlh_json, first_name, last_name, timestamp, school)
                VALUES (1,0,0,0,0,?,?,?,?,?,?,?,?)
        """,
            (
                "mlh:" + str(mlh_id),
                session["mlh_info"]["email"],
                session["mlh_info"]["email"],
                dumps(session["mlh_info"]),
                session["mlh_info"]["first_name"],
                session["mlh_info"]["last_name"],
                int(time.time() * 1000),
                school_name,
            ),
        )
        c.connection.commit()
        flasher(
            "Imported data from MLH. Please double check it's correct!", color="success"
        )
    else:
        pass
    # not first login, we're good

    session["email"] = email

    if "post_login_redirect" in session:
        redir = session.pop("post_login_redirect", None)
        return redirect(url_for(redir))

    return redirect(url_for("hacker.application"))


@bp.route("/import/gh")
@hacker_login_required
def init_gh():
    c = get_db().cursor()

    print("gh_info", session["gh_info"])
    email = session["gh_info"]["email"]

    c.execute("SELECT COUNT(1) FROM Applicants WHERE email=?", (email,))
    if c.fetchone()[0] != 1:
        # first login, init profile
        c.execute(
            """
            INSERT INTO Applicants
                (verified, admin, adult, completed, admitted, user_id, email, contact_email, gh_json, timestamp)
            VALUES (1,0,0,0,0,?,?,?,?,?)
        """,
            (
                "gh:" + str(session["gh_info"]["id"]),
                email,
                email,
                dumps(session["gh_info"]),
                int(time.time() * 1000),
            ),
        )
        c.connection.commit()

        flasher(
            "Imported data from Github. Please double check it's correct!",
            color="success",
        )
    else:
        pass
    # we should load the profile maybe

    session["email"] = email

    if "post_login_redirect" in session:
        redir = session.pop("post_login_redirect", None)
        return redirect(url_for(redir))

    return redirect(url_for("hacker.application"))


def resolve_application(email):
    c = get_db().cursor()
    c.execute("SELECT * FROM Applicants WHERE email=?", (email,))
    row = c.fetchone()

    row_text = {}
    for key in row.keys():
        row_text[key] = "" if row[key] is None else row[key]

    return row, row_text


@bp.route("/application")
@hacker_login_required
def application():
    appl, appl_text = resolve_application(session["email"])

    if appl["completed"]:
        completed_time = arrow.get(
            appl["completed_time"]).format("MMM D, YYYY hh:mm a")
    else:
        completed_time = ""

    return render_template(
        "hacker/form.html",
        appl=appl_text,
        completed_time=completed_time,
        login_type=capitalize_login_provider(),
    )


@bp.route("/discord")
@hacker_login_required
def discord():
    appl, appl_text = resolve_application(session["email"])

    c = get_db().cursor()
    c.execute(
        """
        SELECT * FROM Invites WHERE app_id=?
    """,
        [appl["user_id"]],
    )

    invite = c.fetchone()

    return render_template(
        "hacker/discord.html",
        appl=appl_text,
        invite=invite,
        login_type=capitalize_login_provider(),
    )


@bp.route("/phone")
@hacker_login_required
def phone():
    appl, appl_text = resolve_application(session["email"])

    return render_template(
        "hacker/phone.html", appl=appl_text, login_type=capitalize_login_provider()
    )


@bp.route("/phone/submit", methods=["POST"])
@hacker_login_required
def phone_submit():
    appl, appl_text = resolve_application(session["email"])

    db = get_db()
    c = db.cursor()

    phone = request.form["phone"]
    if phone is None:
        flasher("No phone number provided!", color="danger")
        return redirect(url_for("hacker.phone"))

    c.execute(
        """
        UPDATE Applicants
            SET address_phone=?
            WHERE user_id=?
    """,
        [phone, appl["user_id"]],
    )
    c.connection.commit()

    flasher("Saved phone number successfully!", color="success")
    return redirect(url_for("hacker.phone"))


def s3_upload(filename, local_fn, tmpdir):

    s3 = boto3.client(
        "s3",
        region_name=current_app.config["S3_REGION"],
        endpoint_url=current_app.config["S3_ENDPOINT"],
        aws_access_key_id=current_app.config["S3_ACCESS_KEY"],
        aws_secret_access_key=current_app.config["S3_ACCESS_SECRET"],
    )

    response = s3.upload_file(
        local_fn,
        current_app.config["S3_BUCKET"],
        filename,
        ExtraArgs={"ContentType": "application/pdf", "ACL": "public-read"},
    )

    shutil.rmtree(tmpdir)


def write_application(submit=False):
    db = get_db()
    c = db.cursor()

    appl_old, _ = resolve_application(session["email"])

    cfg = get_config(db)
    if cfg["applications_dline"] <= time.time():
        flasher("Application deadline has passed!", color="danger")
        return redirect(url_for("hacker.application"))

    # Validation
    form = IncompleteApplicationForm(request.form)
    if not form.validate():
        for field in form:
            for error in field.errors:
                flasher("%s: %s" % (field.label.text, error), "danger")
        for error in form.form_errors:
            flasher(error)

        return False
    elif submit:
        form = ApplicationForm(request.form)
        if not form.validate():
            for field in form:
                for error in field.errors:
                    flasher("%s: %s" % (field.label.text, error), "danger")
            for error in form.form_errors:
                flasher(error)
            submit = False

    if request.files["resume"].filename != "":
        # TODO: More file validation

        filename = f"htb21-cvs/{'_'.join(appl_old['user_id'].split(':'))}.pdf"

        # HAX - S3 upload is slow as fuck, so i'm doing it in the background
        # and just hoping it works
        tmpdir = tempfile.mkdtemp()
        local_fn = os.path.join(tmpdir, filename.split("/")[1])
        request.files["resume"].save(local_fn)
        upload = Process(target=s3_upload, args=(filename, local_fn, tmpdir))

        upload.daemon = True
        upload.start()

        # oh jesus
        resume = f"{current_app.config['S3_SUBDOMAIN']}/{filename}"
        # we're going to set this separately to avoid overriding existing values
        c.execute(
            """
            UPDATE Applicants
                SET resume=?
                WHERE email=?
        """,
            (resume, session["email"]),
        )

    try:

        # checkboxes
        cb_gdpr = "gdpr" in request.form and request.form["gdpr"] == "on"
        cb_gdpr_sponsor = (
            "gdpr_sponsor" in request.form and request.form["gdpr_sponsor"] == "on"
        )
        cb_mlh_coc = "mlh_coc" in request.form and request.form["mlh_coc"] == "on"
        cb_mlh_admin = "mlh_admin" in request.form and request.form["mlh_admin"] == "on"
        cb_mlh_email = "mlh_email" in request.form and request.form["mlh_email"] == "on"
        cb_adult = "adult" in request.form and request.form["adult"] == "on"
        cb_hackuk_admin = (
            "hackuk_admin" in request.form and request.form["hackuk_admin"] == "on"
        )
        cb_hackuk_email = (
            "hackuk_email" in request.form and request.form["hackuk_email"] == "on"
        )
        cb_vaccinated = (
            "vaccinated" in request.form and request.form["vaccinated"] == "on"
        )

        dd_gradYear = request.form["gradYear"] if "gradYear" in request.form else None
        dd_shirt_size = (
            request.form["shirt_size"] if "shirt_size" in request.form else None
        )

        c.execute(
            """
            UPDATE Applicants
                SET first_name=?,
                    last_name=?,
                    contact_email=?,
                    school=?,
                    gradYear=?,
                    shirt_size=?,
                    allergens=?,
                    address_line_1=?,
                    address_line_2=?,
                    address_line_3=?,
                    address_city=?,
                    address_region=?,
                    address_country=?,
                    address_pcode=?,
                    address_phone=?,
                    description=?,
                    essay=?,
                    gdpr=?,
                    gdpr_sponsor=?,
                    mlh_coc=?,
                    mlh_admin=?,
                    mlh_email=?,
                    adult=?,
                    hackuk_admin=?,
                    hackuk_email=?,
                    vaccinated=?,
                    completed=?,
                    completed_time=?
                WHERE
                    email=?
        """,
            [
                request.form["first_name"],
                request.form["last_name"],
                request.form["contact_email"],
                request.form["school"],
                dd_gradYear,
                dd_shirt_size,
                request.form["allergens"],
                request.form["address_line_1"],
                request.form["address_line_2"],
                request.form["address_line_3"],
                request.form["address_city"],
                request.form["address_region"],
                request.form["address_country"],
                request.form["address_pcode"],
                request.form["phone"],
                request.form["description"],
                request.form["essay"],
                cb_gdpr,
                cb_gdpr_sponsor,
                cb_mlh_coc,
                cb_mlh_admin,
                cb_mlh_email,
                cb_adult,
                cb_hackuk_admin,
                cb_hackuk_email,
                cb_vaccinated,
                1 if submit else 0,
                (time.time()) if submit else None,
                session["email"],
            ],
        )
        c.connection.commit()

        if submit:
            flasher("Submitted successfully!", color="success")
        else:
            flasher("Saved successfully!", color="success")
    except Exception as e:
        raise e
        print(e)
        flasher(
            "Something went wrong! Please contact tech@hacktheburgh.com.",
            color="danger",
        )

    return redirect(url_for("hacker.application"))


@bp.route("/application/submit", methods=["POST"])
@hacker_login_required
def submit_application():
    write_application(submit=True)
    return redirect(url_for("hacker.application"))


@bp.route("/application/save", methods=["POST"])
@hacker_login_required
def save_application():
    write_application(submit=False)
    return redirect(url_for("hacker.application"))


@bp.route("/status")
@hacker_login_required
def status():
    appl, appl_text = resolve_application(session["email"])

    if appl["completed"]:
        completed_time = arrow.get(
            appl["completed_time"]).format("MMM D, YYYY hh:mm a")
    else:
        completed_time = ""

    return render_template(
        "hacker/status.html",
        appl=appl_text,
        completed_time=completed_time,
        login_type=capitalize_login_provider(),
    )


@bp.route("/invites")
@hacker_login_required
def invites():
    appl, appl_text = resolve_application(session["email"])

    c = get_db().cursor()
    c.execute(
        """
        SELECT * FROM Invites WHERE app_id=?
    """,
        [appl["user_id"]],
    )

    rows = c.fetchall()
    if rows is None:
        rows = []

    return render_template(
        "hacker/invites.html",
        appl=appl_text,
        invites=rows,
        login_type=capitalize_login_provider(),
    )


@bp.route("/resume")
@hacker_login_required
def show_resume():
    # this exists solely for people who click the link too fast
    # (before it has a chance to upload)
    appl, _ = resolve_application(session["email"])
    print(appl["resume"])
    if appl["resume"] is not None and appl["resume"] != "":
        resp = requests.head(appl["resume"])
        if resp.status_code != 403:
            return redirect(appl["resume"])
        else:
            return "Resume processing, please try again in a few seconds."
    else:
        return "You haven't uploaded a resume!"


@bp.route("/resume/delete")
@hacker_login_required
def delete_resume():
    appl, _ = resolve_application(session["email"])

    db = get_db()
    cfg = get_config(db)
    if cfg["applications_dline"] <= time.time():
        flasher("Application deadline has passed!", color="danger")
        return redirect(url_for("hacker.application"))

    if appl["resume"] is not None and appl["resume"] != "":
        filename = f"htb22-cvs/{'_'.join(appl['user_id'].split(':'))}.pdf"

        s3 = boto3.client(
            "s3",
            region_name=app.config["S3_REGION"],
            endpoint_url=app.config["S3_ENDPOINT"],
            aws_access_key_id=app.config["S3_ACCESS_KEY"],
            aws_secret_access_key=app.config["S3_ACCESS_SECRET"],
        )

        s3.delete_object(
            Bucket=app.config["S3_BUCKET"],
            Key=filename,
        )

        c = db.cursor()
        c.execute(
            """
            UPDATE Applicants
                SET resume=NULL
                WHERE email=?
        """,
            [session["email"]],
        )
        c.connection.commit()

        flasher("Resume deleted successfully.", "success")

        return redirect(url_for("hacker.application"))
    else:
        return "You haven't uploaded a resume!"
