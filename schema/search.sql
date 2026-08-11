CREATE TABLE IF NOT EXISTS search_works (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  language TEXT,
  published TEXT,
  format TEXT,
  quality TEXT NOT NULL,
  edition_count INTEGER NOT NULL DEFAULT 0,
  sources_json TEXT NOT NULL DEFAULT '[]',
  cover_url TEXT,
  updated_at INTEGER NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_works_fts USING fts5(
  id UNINDEXED,
  title,
  author,
  tokenize='unicode61 remove_diacritics 2'
);

CREATE INDEX IF NOT EXISTS search_works_language ON search_works(language);
CREATE INDEX IF NOT EXISTS search_works_published ON search_works(published);
CREATE INDEX IF NOT EXISTS search_works_quality ON search_works(quality);
