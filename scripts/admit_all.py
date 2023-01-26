#!/usr/bin/env python
# Admits users from a .csv file with their email addresses in.
# Emails should be in the first column and can be login or contact emails.

from csv import reader
from sys import argv
import requests

SERVER_BASE = "https://register.2023.hacktheburgh.com/"
API_KEY = getenv("HTB_API_KEY")
API_SECRET = getenv("HTB_API_SECRET")

session = requests.Session()

session.headers.update({'Authorization': "Bearer %s/%s" % (API_KEY, API_SECRET)})

if len(argv) != 2:
    print("Usage: ./admit_all.py admitted.csv")
    exit(1)

filename = argv[1]
f = open(filename, "r")
r = reader(f)

def get_user_by_email(email):
    r = session.get(SERVER_BASE + f"api/v2/applicants/by_email?email={email}").json()
    if r['ok']:
        return r['data']
    else:
        raise Exception(r['message'])

def admit_user_id(i):
    r = session.post(SERVER_BASE + "api/v2/applicants/admit", json={'app_id': i, 'admit': True}).json()
    if r['ok']:
        return True
    else:
        raise Exception(r['message'])
    pass

for row in r:
    email = row[0]
    try:
        user = get_user_by_email(email)
        print(f"{email} - {user['user_id']}")
        assert admit_user_id(user['user_id'])
    except Exception as e:
        print("Error admitting %s: %s" % (email, str(e)))
