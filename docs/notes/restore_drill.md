# Restore drill, 2026-09-21 00:08Z

One run of `scripts/backup_db.sh` and `scripts/restore_db.sh` against a throwaway Postgres 16
container (`docker run -d --name sl-pg-test -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:16-alpine`),
migrated with `uv run alembic -c apps/api/alembic.ini upgrade head`. The container was removed afterwards.
Client tools: pg_dump and pg_restore 18.6 from Homebrew libpq (the machine had none).

## What happened

1. Seeded 5 sessions, 16 answers and 1 contributor token through the API itself (TestClient, no server started).
2. `bash scripts/backup_db.sh` wrote `data/backups/sl-20260921T000836Z.dump` (19517 bytes, pg_dump custom format).
3. Deleted every study row and reset the randomization counter, so the database looked like the loss we fear.
4. `bash scripts/restore_db.sh <file>` took a safety copy first, then restored. Row counts came back to 5, 16, 1 and the counter to 5.
5. `GET /api/test/counts` on the restored database answered with the same counts as before.

## Two bugs the drill found and fixed

- The safety copy inside restore_db.sh used the same timestamp as the file being restored, so when both landed in the same second it overwrote the backup and then restored the empty copy (seen first on SQLite: 0 rows after restore). Fixed with a `-before-restore-<pid>` label on safety copies and a stop if the paths would collide.
- pg_restore 18 emits `SET transaction_timeout = 0`, which Postgres 16 rejects. The data still restored but the script exited 1 before its last line. Fixed by streaming pg_restore's SQL through psql with that one line filtered and `ON_ERROR_STOP` on, so any real error still stops the restore.

## SQLite

The same two scripts were run on the default `sqlite:///./data/local.db`: one row inserted, backed up with `sqlite3 .backup`, deleted, restored, `PRAGMA integrity_check` ok, row back.

## Transcript (Postgres, trimmed)

```
== 1. seed through the API (TestClient, Postgres on :5433)
sessions created: 5, responses: 16, observer tokens: 1, correct_total: 8
== 2. rows before backup
5|16|1|5
== 3. bash scripts/backup_db.sh
backup_db: wrote /Users/alexvintera/second-look/data/backups/sl-20260921T000836Z.dump (19517 bytes)
== 4. simulate the loss: delete every study row
DELETE 16
DELETE 1
DELETE 5
UPDATE 1
0|0|0|0
== 5. bash scripts/restore_db.sh /Users/alexvintera/second-look/data/backups/sl-20260921T000836Z.dump
restore_db: safety copy of the current database first
backup_db: wrote /Users/alexvintera/second-look/data/backups/sl-20260921T000837Z-before-restore-25017.dump (18751 bytes)
pg_restore: error: could not execute query: ERROR:  unrecognized configuration parameter "transaction_timeout"
Command was: SET transaction_timeout = 0;
== 6. rows after restore
5|16|1|5
== 7. the API still answers on the restored database
{'by_arm': {'untrained': {'randomized': 3, 'completed': 0}, 'trained': {'randomized': 2, 'completed': 1}}, 'by_source': {'poster': 1, 'chat': 0, 'friends': 0, 'creek_group': 0, 'other': 0}, 'post_lock': 0}
== 8. second pass after fixing the version mismatch in restore_db.sh
delete every study row again
0|0|0|0
== bash scripts/restore_db.sh /Users/alexvintera/second-look/data/backups/sl-20260921T000836Z.dump
restore_db: safety copy of the current database first
backup_db: wrote /Users/alexvintera/second-look/data/backups/sl-20260921T000911Z-before-restore-25235.dump (18727 bytes)
 set_config 
restore_db: restored from /Users/alexvintera/second-look/data/backups/sl-20260921T000836Z.dump
exit code: 0
== rows after restore
5|16|1|5
```

## Still to do by a human

- Schedule `bash scripts/backup_db.sh` daily on the host (the compose stack or Fly) and keep `data/backups/` private. Nobody computes outcomes from backups.
- Schedule `uv run python scripts/cleanup_uploads.py` daily beside it.
- In production the server and the client tools should be the same major version; then the filtered line never appears.
