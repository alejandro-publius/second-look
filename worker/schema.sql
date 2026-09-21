-- Mirrors apps/api/models.py and the alembic migrations. D1 is SQLite, so the same shapes work.
-- Booleans are INTEGER 0 or 1. Times are ISO 8601 strings in UTC.

CREATE TABLE IF NOT EXISTS arm_slot (
  position INTEGER PRIMARY KEY,
  arm TEXT NOT NULL,
  block_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS counter (
  id INTEGER PRIMARY KEY,
  next_position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS session (
  id TEXT PRIMARY KEY,
  arm TEXT NOT NULL,
  block_id INTEGER NOT NULL,
  item_order TEXT NOT NULL,
  consent_version TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  build_hash TEXT NOT NULL,
  consent_at TEXT NOT NULL,
  started_at TEXT NOT NULL,
  lesson_seconds TEXT,
  completed_at TEXT,
  client_token_hash TEXT NOT NULL,
  ua_class TEXT NOT NULL,
  is_test INTEGER NOT NULL DEFAULT 0,
  source_label TEXT NOT NULL,
  hidden_field_filled INTEGER NOT NULL DEFAULT 0,
  post_lock INTEGER NOT NULL DEFAULT 0,
  prior_experience TEXT,
  warmup_choice TEXT,
  unsent_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS session_token ON session (client_token_hash);

CREATE TABLE IF NOT EXISTS response (
  session_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  answer TEXT NOT NULL,
  rt_ms INTEGER NOT NULL,
  position INTEGER NOT NULL,
  first_choice TEXT,
  t_first_ms INTEGER,
  n_changes INTEGER NOT NULL DEFAULT 0,
  received_at TEXT NOT NULL,
  PRIMARY KEY (session_id, item_id)
);

CREATE TABLE IF NOT EXISTS observer (
  contributor_token TEXT PRIMARY KEY,
  scores_json TEXT NOT NULL,
  tested_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skeleton_ping (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  note TEXT NOT NULL,
  created_at TEXT NOT NULL
);
