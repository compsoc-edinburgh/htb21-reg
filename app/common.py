from flask import flash

def flasher(text, color=None):
    if color is None:
        color = ''
    else:
        color = 'is-' + color
    flash({'text': text, 'type': color})

def get_config(db):
    c = db.cursor()

    c.execute('''
        SELECT * FROM Configuration WHERE id=0
    ''')

    return c.fetchone()
