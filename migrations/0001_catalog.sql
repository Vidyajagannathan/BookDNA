CREATE TABLE IF NOT EXISTS catalog_works (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT NOT NULL DEFAULT 'Unknown author',
  first_publish_year INTEGER,
  cover_id INTEGER,
  subjects_json TEXT NOT NULL DEFAULT '[]',
  source TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS catalog_editions (
  id TEXT PRIMARY KEY,
  work_id TEXT NOT NULL,
  title TEXT NOT NULL,
  publisher TEXT,
  publish_date TEXT,
  language TEXT,
  format TEXT,
  cover_id INTEGER,
  source TEXT NOT NULL,
  FOREIGN KEY (work_id) REFERENCES catalog_works(id)
);

CREATE TABLE IF NOT EXISTS catalog_identifiers (
  scheme TEXT NOT NULL,
  value TEXT NOT NULL,
  edition_id TEXT NOT NULL,
  PRIMARY KEY (scheme, value, edition_id),
  FOREIGN KEY (edition_id) REFERENCES catalog_editions(id)
);

CREATE INDEX IF NOT EXISTS catalog_editions_work ON catalog_editions(work_id);
CREATE INDEX IF NOT EXISTS catalog_identifiers_lookup ON catalog_identifiers(scheme, value);
CREATE INDEX IF NOT EXISTS catalog_works_year ON catalog_works(first_publish_year DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS catalog_works_fts USING fts5(
  id UNINDEXED,
  title,
  author,
  subjects,
  tokenize='unicode61 remove_diacritics 2'
);
