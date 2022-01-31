#!/usr/bin/env python
# Get names, emails, and CV URLs from applicants.
# This data is intended to be given to sponsors, and so it excludes those who haven't agreed to share their info this way.
# By default, only includes those who have been admitted. Pass --all to override this.

from csv import writer
from sys import stdout, argv
from os import getenv
import requests

SERVER_BASE = "https://register.2022.hacktheburgh.com/"
CV_BASE_URL = "https://htb8-test.s3.eu-west-2.amazonaws.com/htb21-cvs/"
API_KEY = getenv("HTB_API_KEY")
API_SECRET = getenv("HTB_API_SECRET")

only_admitted = True
if len(argv) > 1 and argv[1] == "--all":
    only_admitted = False

session = requests.Session()
session.headers.update({'Authorization': "Bearer %s/%s" % (API_KEY, API_SECRET)})

def get_all_users():
    r = session.get(SERVER_BASE + "api/v2/applicants/all/json?completed=1").json()
    if r['ok']:
        return r['data']
    else:
        raise Exception(r['message'])
    pass

w = writer(stdout)
w.writerow(['First Name', 'Last Name(s)', 'Email', 'CV', 'Admitted?'])
for user in get_all_users():
    if (only_admitted and not user['admitted']) or not user['gdpr_sponsor']:
        continue

    cv_url = f"{CV_BASE_URL}{user['user_id'].replace(':', '_')}.pdf"
    if requests.get(cv_url).status_code != 200:
        continue
    w.writerow([user['first_name'], user['last_name'], user['contact_email'], cv_url, user['admitted'] == 1])
