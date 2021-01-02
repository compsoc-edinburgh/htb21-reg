-- Initialize the database

DROP TABLE IF EXISTS Applicants;
DROP TABLE IF EXISTS Votes;

CREATE TABLE Applicants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mongo_id    TEXT NOT NULL,
    mlh_id      TEXT NOT NULL,

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

    -- authorizations
    gdpr            INTEGER,
    mlh_coc         INTEGER,
    hackuk_admin    INTEGER,
    hackuk_mail     INTEGER,


    UNIQUE (mongo_id)
);


CREATE TABLE Votes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rating          INTEGER NOT NULL,
    author          TEXT NOT NULL,
    author_email    TEXT NOT NULL,
    app_id          TEXT,

    FOREIGN KEY (app_id) REFERENCES Applicants (mongo_id)
        ON DELETE CASCADE ON UPDATE NO ACTION,
    UNIQUE (author, app_id)
);
