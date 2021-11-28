from flask import flash


def flasher(text, color=None):
    """Show a message on the next page"""
    if color is None:
        color = ""
    else:
        color = "is-" + color
    flash({"text": text, "type": color})


def get_config(db):
    """Get the configuration singleton object from the database"""
    c = db.cursor()

    c.execute(
        """
        SELECT * FROM Configuration WHERE id=0
    """
    )

    return c.fetchone()


def row_to_obj(row):
    """Convert a database row to an object/dict."""
    obj = {}
    for key in row.keys():
        obj[key] = row[key]
    return obj


def rows_to_objs(rows):
    """Convert an iterator over rows to a list of objects/dicts"""
    objs = []
    for row in rows:
        objs.append(row_to_obj(row))
    return objs
