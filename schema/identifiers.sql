CREATE TABLE IF NOT EXISTS catalog_identifiers (
  scheme TEXT NOT NULL,
  value TEXT NOT NULL,
  edition_id TEXT NOT NULL,
  work_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY (scheme, value, edition_id)
);

CREATE INDEX IF NOT EXISTS catalog_identifiers_value ON catalog_identifiers(scheme, value);
