from csv import DictReader, DictWriter
from io import StringIO
from .common import row_to_obj
import functools
import tempfile
import os

# helper to map from column names in the CSV dump to the schema
dumpNameMapping = {
    "_id": "mongo_id",
    "admin": "admin",
    "profile.adult": "adult",
    "status.completedProfile": "completed",
    "status.admitted": "admitted",
    "verified": "verified",
    "timestamp": "timestamp",
    "email": "email",
    "profile.name": "name",
    "profile.school": "school",
    "profile.graduationYear": "gradYear",
    "profile.gender": "gender",
    "profile.description": "description",
    "profile.essay": "essay",
}


def get_applicants_from_csv(csv_bytes):
    # while it may be cleaner to do this in memory, it Just Doesn't Work Properly (tm) without hitting disk first--i suspect it has something to do with character encodings
    with tempfile.TemporaryDirectory() as tempdir:
        fn = os.path.join(tempdir, "dump.csv")
        csv_bytes.save(fn)
        dr = DictReader(open(fn))

    for row in dr:
        translated = {}

        for key in dumpNameMapping:
            if row[key] == "true":
                translated[dumpNameMapping[key]] = 1
            elif row[key] == "false":
                translated[dumpNameMapping[key]] = 0
            else:
                translated[dumpNameMapping[key]] = row[key]

        yield translated


def insert_applicant(cursor, applicant):
    cols = [
        "mongo_id",
        "admin",
        "adult",
        "completed",
        "admitted",
        "verified",
        "timestamp",
        "email",
        "name",
        "school",
        "gradYear",
        "gender",
        "description",
        "essay",
    ]

    cols = list(map(lambda k: applicant[k], cols))

    cursor.execute(
        """
        INSERT INTO Applicants (
            mongo_id,
            admin,
            adult,
            completed,
            admitted,
            verified,
            timestamp,
            email,
            name,
            school,
            gradYear,
            gender,
            description,
            essay
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        cols,
    )


def create_csv(conn):
    c = conn.cursor()
    c.execute(
        """
        SELECT * FROM Applicants WHERE completed=1
    """
    )
    rows = c.fetchall()
    if rows is None:
        rows = []

    out = []
    for row in rows:
        c.execute(
            """
            SELECT rating
            FROM Votes
            WHERE
                app_id=?
        """,
            (row["user_id"],),
        )
        votes = c.fetchall()

        # i don't remember why i did this but there must have been a reason...
        if len(votes) != 0:
            voteaverage = functools.reduce(
                lambda a, v: a + v["rating"], votes, 0
            ) / len(votes)
            voteaverage = float("{:.3}".format(voteaverage))
        else:
            voteaverage = 0

        obj = row_to_obj(row)
        obj["votes"] = voteaverage
        out.append(obj)

    buf = StringIO()

    csv = DictWriter(buf, fieldnames=out[0].keys())
    csv.writeheader()
    for app in out:
        csv.writerow(app)

    csv_text = buf.getvalue()
    buf.close()
    return csv_text
