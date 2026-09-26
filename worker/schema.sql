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

-- The creek check (Update 10 answer A3). Mirrors apps/api/models.py. Coordinates are rounded to
-- about 1 km unless the person placed the pin. No name, address or token beyond the random
-- contributor token the person chose to keep.

CREATE TABLE IF NOT EXISTS spot (
  spot_id TEXT PRIMARY KEY,
  spot_name TEXT NOT NULL,
  reach_id TEXT NOT NULL,
  reach_name TEXT NOT NULL,
  creek_id TEXT NOT NULL,
  creek_name TEXT NOT NULL,
  latitude REAL,
  longitude REAL,
  coarse INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visit (
  visit_id TEXT PRIMARY KEY,
  spot_id TEXT NOT NULL REFERENCES spot (spot_id),
  kind TEXT NOT NULL,
  contributor_token TEXT,
  answered_at TEXT NOT NULL,
  answers_json TEXT NOT NULL,
  first_rating TEXT,
  final_rating TEXT,
  photo_ids_json TEXT NOT NULL,
  followups_json TEXT NOT NULL,
  site_json TEXT NOT NULL,
  finalized_at TEXT,
  software_version TEXT NOT NULL DEFAULT '0.1.0',
  -- The language the questions were shown in (UPDATE_32 section 2). A database made before it
  -- gains the column once from migrations/0001_visit_language.sql.
  language TEXT
);

CREATE INDEX IF NOT EXISTS visit_spot ON visit (spot_id);

CREATE TABLE IF NOT EXISTS check_result (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  visit_id TEXT NOT NULL REFERENCES visit (visit_id),
  rule_id TEXT NOT NULL,
  asked INTEGER NOT NULL DEFAULT 1,
  question_text TEXT,
  answer TEXT,
  detail_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS check_result_visit ON check_result (visit_id);

-- Our store of validated FHIR JSON: one Bundle per finalized visit, the source of truth the
-- sandbox mirrors. On the Python side this is a folder of files; here it is a table.
CREATE TABLE IF NOT EXISTS fhir_bundle (
  visit_id TEXT PRIMARY KEY REFERENCES visit (visit_id),
  spot_id TEXT NOT NULL,
  bundle_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS fhir_bundle_spot ON fhir_bundle (spot_id);

-- A photo lives in KV under its id; this row holds the hash of the one token that can read it.
CREATE TABLE IF NOT EXISTS upload (
  photo_id TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

-- What GET /api/two last fetched from the sandbox, so the screen still works when it is down.
CREATE TABLE IF NOT EXISTS sandbox_cache (
  cache_key TEXT PRIMARY KEY,
  body TEXT NOT NULL,
  status TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);

-- A short summary of iNaturalist sightings near each creek, as scripts/cache_inaturalist.py
-- fetched it on the Mac, for the context line on the record page and /city. One row per creek.
-- Context only: nothing counts it and nothing decides from it (docs/adr/0011-inaturalist-context.md).
CREATE TABLE IF NOT EXISTS inaturalist_cache (
  creek TEXT PRIMARY KEY,
  body TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);

-- A finished video walk's demo record (UPDATE_30 section 1 item 3), so its link opens on any
-- device. A table of its own: nothing that counts, maps or mirrors creek checks reads it. The
-- answers are coded values from the form's lists; there is no token, no position and no free
-- text. Each row is deleted after delete_after, 30 days after it was stored. Safe to run again.
CREATE TABLE IF NOT EXISTS walk_record (
  record_id TEXT PRIMARY KEY,
  walk_id TEXT NOT NULL,
  answered_at TEXT NOT NULL,
  answers_json TEXT NOT NULL,
  bundle_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  delete_after TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS walk_record_created ON walk_record (created_at);
CREATE INDEX IF NOT EXISTS walk_record_delete_after ON walk_record (delete_after);

-- The follow-up checks a finished walk ran, as a creek check keeps its own in check_result, and
-- its final rating (judge walk W01). One row per walk record, written in the same batch as it and
-- deleted with it. The questions are the locale's, the answers coded values; no free text.
-- Additive and safe to run again.
CREATE TABLE IF NOT EXISTS walk_checks (
  record_id TEXT PRIMARY KEY,
  final_rating TEXT,
  checks_json TEXT NOT NULL
);

-- Part 2, the assisted second look (UPDATE_31, docs/analysis_plan_v2.md). One row per part 1
-- session that was offered it and chose: declined rows have no arm. The slots come from
-- worker/part2_arms.sql, written by scripts/seed_part2_arms.py from core/allocator.py, one
-- sequence per part 1 arm. Safe to run again.
CREATE TABLE IF NOT EXISTS part2_slot (
  stratum TEXT NOT NULL,
  position INTEGER NOT NULL,
  arm TEXT NOT NULL,
  block_id INTEGER NOT NULL,
  PRIMARY KEY (stratum, position)
);

CREATE TABLE IF NOT EXISTS part2_counter (
  stratum TEXT PRIMARY KEY,
  next_position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS part2_session (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL UNIQUE,
  part1_arm TEXT NOT NULL,
  arm TEXT,
  block_id INTEGER,
  item_order TEXT,
  offered_at TEXT NOT NULL,
  declined INTEGER NOT NULL DEFAULT 0,
  started_at TEXT,
  completed_at TEXT,
  client_token_hash TEXT NOT NULL,
  is_test INTEGER NOT NULL DEFAULT 0,
  post_lock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS part2_response (
  part2_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  position INTEGER NOT NULL,
  first_answer TEXT NOT NULL,
  final_answer TEXT,
  question_shown INTEGER NOT NULL,
  choice TEXT NOT NULL DEFAULT '',
  t_first_ms INTEGER,
  t_final_ms INTEGER,
  received_at TEXT NOT NULL,
  PRIMARY KEY (part2_id, item_id)
);
