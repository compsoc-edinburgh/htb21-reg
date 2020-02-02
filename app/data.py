from csv import DictReader
import tempfile
import os

# helper to map from column names in the CSV dump to the schema
dumpNameMapping = {
    '_id': 'mongo_id',
    'admin': 'admin',
    'profile.adult': 'adult',
    'status.completedProfile': 'completed',
    'status.admitted': 'admitted',
    'verified': 'verified',
    'timestamp': 'timestamp',
    'email': 'email',
    'profile.name': 'name',
    'profile.school': 'school',
    'profile.graduationYear': 'gradYear',
    'profile.gender': 'gender',
    'profile.description': 'description',
    'profile.essay': 'essay'
}

def get_applicants_from_csv(csv_bytes):

    # while it may be cleaner to do this in memory, it Just Doesn't Work Properly (tm) without hitting disk first--i suspect it has something to do with character encodings

    with tempfile.TemporaryDirectory() as tempdir:
        fn = os.path.join(tempdir, 'dump.csv')
        csv_bytes.save(fn)
        dr = DictReader(open(fn))

    for row in dr:
        translated = {}
        
        for key in dumpNameMapping:
            if row[key] == 'true':
                translated[dumpNameMapping[key]] = 1
            elif row[key] == 'false':
                translated[dumpNameMapping[key]] = 0
            else:
                translated[dumpNameMapping[key]] = row[key]

        yield translated


def insert_applicant(cursor, applicant):
    cols = [
        'mongo_id',
        'admin',
        'adult',
        'completed',
        'admitted',
        'verified',
        'timestamp',
        'email',
        'name',
        'school',
        'gradYear',
        'gender',
        'description',
        'essay'
    ]

    cols = list(map( lambda k: applicant[k], cols) )

    cursor.execute('''
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
    ''', cols)

