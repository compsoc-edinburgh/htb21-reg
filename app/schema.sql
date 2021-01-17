-- Initialize the database

DROP TABLE IF EXISTS Applicants;
DROP TABLE IF EXISTS Votes;
DROP TABLE IF EXISTS Services;
DROP TABLE IF EXISTS Configuration;


CREATE TABLE Applicants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,

    -- meta
    admin           INTEGER,
    adult           INTEGER,
    completed       INTEGER,
    admitted        INTEGER,
    verified        INTEGER,
    timestamp       TEXT,
    email           TEXT,
    contact_email   TEXT,
    mlh_json        TEXT,
    gh_json         TEXT,

    -- address
    address_line1   TEXT,
    address_line2   TEXT,
    address_line3   TEXT,
    address_city    TEXT,
    address_region  TEXT,
    address_pcode   TEXT,
    address_country TEXT,
    address_phone   TEXT,

    -- profile
    first_name  TEXT,
    last_name   TEXT,
    school      TEXT,
    gradYear    TEXT,
    gender      TEXT,
    description TEXT,
    essay       TEXT,
    shirt_size  TEXT,

    -- authorizations
    gdpr            INTEGER,
    mlh_coc         INTEGER,
    hackuk_admin    INTEGER,
    hackuk_email     INTEGER,

    UNIQUE (user_id),
    UNIQUE (email)
);


CREATE TABLE Votes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rating          INTEGER NOT NULL,
    author          TEXT NOT NULL,
    author_email    TEXT NOT NULL,
    app_id          TEXT,

    FOREIGN KEY (app_id) REFERENCES Applicants (user_id)
        ON DELETE CASCADE ON UPDATE NO ACTION,
    UNIQUE (author, app_id)
);


CREATE TABLE Services (
    api_key         TEXT NOT NULL,
    api_secret      TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    author_email    TEXT NOT NULL,
    created         INTEGER NOT NULL,

    UNIQUE(api_key),
    UNIQUE(display_name)
);


CREATE TABLE Configuration (
    id                 INTEGER PRIMARY KEY DEFAULT 0,

    applications_open  INTEGER NOT NULL,
    applications_dline INTEGER NOT NULL,
    event_start        INTEGER NOT NULL
);

-- default config
INSERT INTO Configuration(id, applications_open, applications_dline, event_start) 
    VALUES (0,0,1613260800,1615032000);
