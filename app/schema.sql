-- Initialize the database

DROP TABLE IF EXISTS Applicants;
DROP TABLE IF EXISTS Votes;

CREATE TABLE Applicants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mongo_id    TEXT NOT NULL,

    -- fields here are from the CSV dump

    -- meta
    admin       INTEGER,
    adult       INTEGER,
    completed   INTEGER,
    admitted    INTEGER,
    verified    INTEGER,
    timestamp   TEXT,
    email       TEXT,

    -- profile
    name        TEXT,
    school      TEXT,
    gradYear    TEXT,
    gender      TEXT,
    description TEXT,
    essay       TEXT,

    UNIQUE (mongo_id)
);


CREATE TABLE Votes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    rating  INTEGER NOT NULL,
    app_id  INTEGER,
    FOREIGN KEY (app_id) REFERENCES Applicants (id)
        ON DELETE CASCADE ON UPDATE NO ACTION
);
