#!/usr/bin/env bash
# Restore the database named by DATABASE_URL from a file made by scripts/backup_db.sh.
#   bash scripts/restore_db.sh data/backups/sl-20260920T170000Z.dump
# A safety backup of the current database is taken first, so a wrong file can be undone.
# Postgres: pg_restore --clean drops and recreates our tables. SQLite: the file is copied over.
set -euo pipefail

if [ $# -lt 1 ] || [ ! -f "$1" ]; then
  echo "usage: bash scripts/restore_db.sh <backup file>" >&2
  exit 2
fi
FILE="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -z "${DATABASE_URL:-}" ] && [ -f "$ROOT/.env" ]; then
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ROOT/.env" | tail -1 | cut -d= -f2- | tr -d '"' || true)"
fi
DATABASE_URL="${DATABASE_URL:-sqlite:///./data/local.db}"

echo "restore_db: safety copy of the current database first"
SAFETY="$(DATABASE_URL="$DATABASE_URL" BACKUP_DIR="${BACKUP_DIR:-$ROOT/data/backups}" BACKUP_LABEL="-before-restore-$$" bash "$ROOT/scripts/backup_db.sh" || true)"
case "$SAFETY" in *"wrote $FILE "*) echo "restore_db: the safety copy would overwrite $FILE, stopping" >&2; exit 1;; esac
echo "${SAFETY:-restore_db: no current database to copy}"

find_tool() {
  if command -v "$1" >/dev/null 2>&1; then command -v "$1"; return; fi
  for dir in /opt/homebrew/opt/libpq/bin /usr/local/opt/libpq/bin /usr/lib/postgresql/*/bin; do
    if [ -x "$dir/$1" ]; then echo "$dir/$1"; return; fi
  done
  echo "restore_db: $1 not found. Install postgresql client tools (brew install libpq)." >&2
  exit 1
}

case "$DATABASE_URL" in
  sqlite:*)
    case "$FILE" in *.dump) echo "restore_db: $FILE is a Postgres dump, DATABASE_URL is SQLite" >&2; exit 1;; esac
    DB_PATH="${DATABASE_URL#sqlite:///}"
    case "$DB_PATH" in ./*) DB_PATH="$ROOT/${DB_PATH#./}";; esac
    mkdir -p "$(dirname "$DB_PATH")"
    rm -f "$DB_PATH-wal" "$DB_PATH-shm"
    cp "$FILE" "$DB_PATH"
    if command -v sqlite3 >/dev/null 2>&1; then
      sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | head -1 | sed 's/^/restore_db: integrity /'
    fi
    ;;
  postgres*|postgresql*)
    case "$FILE" in *.sqlite) echo "restore_db: $FILE is a SQLite copy, DATABASE_URL is Postgres" >&2; exit 1;; esac
    PG_URL="${DATABASE_URL/postgresql+psycopg:\/\//postgresql://}"
    PG_URL="${PG_URL/postgres+psycopg:\/\//postgresql://}"
    PG_RESTORE="$(find_tool pg_restore)"
    PSQL="$(find_tool psql)"
    # pg_restore writes plain SQL; psql applies it and stops on the first real error. The one
    # filtered line is a setting newer client tools emit that older servers do not know.
    "$PG_RESTORE" --clean --if-exists --no-owner --no-acl -f - "$FILE" \
      | grep -v '^SET transaction_timeout' \
      | "$PSQL" -q -o /dev/null -v ON_ERROR_STOP=1 "$PG_URL"
    ;;
  *)
    echo "restore_db: DATABASE_URL must start with sqlite or postgresql" >&2
    exit 1
    ;;
esac
echo "restore_db: restored from $FILE"
