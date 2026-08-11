CREATE TABLE IF NOT EXISTS catalog_runs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  started_at INTEGER NOT NULL,
  completed_at INTEGER
);

CREATE TABLE IF NOT EXISTS catalog_source_stats (
  source TEXT PRIMARY KEY,
  seen INTEGER NOT NULL DEFAULT 0,
  accepted INTEGER NOT NULL DEFAULT 0,
  rejected INTEGER NOT NULL DEFAULT 0,
  last_refresh INTEGER
);

CREATE TABLE IF NOT EXISTS catalog_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT OR IGNORE INTO catalog_settings VALUES ('mode', 'shadow');
