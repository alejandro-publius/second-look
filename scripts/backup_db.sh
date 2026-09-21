#!/usr/bin/env bash
# Back up the database named by DATABASE_URL into data/backups/ with a UTC timestamp.
#   bash scripts/backup_db.sh            -> prints the path of the new backup file
# Postgres: pg_dump custom format (.dump). SQLite: a consistent copy (.sqlite).
# Never prints the URL, because it can hold a password. Backups stay private (data/ is gitignored).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -z "${DATABASE_URL:-}" ] && [ -f "$ROOT/.env" ]; then
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ROOT/.env" | tail -1 | cut -d= -f2- | tr -d '"' || true)"
fi
DATABASE_URL="${DATABASE_URL:-sqlite:///./data/local.db}"
OUT_DIR="${BACKUP_DIR:-$ROOT/data/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
# BACKUP_LABEL is added to the file name; restore_db.sh uses it so a safety copy never
# overwrites the file being restored when both land in the same second.
LABEL="${BACKUP_LABEL:-}"
mkdir -p "$OUT_DIR"

find_tool() {
  # $1 = tool name. Looks in PATH, then in the Homebrew libpq keg, which brew does not link.
  if command -v "$1" >/dev/null 2>&1; then command -v "$1"; return; fi
  for dir in /opt/homebrew/opt/libpq/bin /usr/local/opt/libpq/bin /usr/lib/postgresql/*/bin; do
    if [ -x "$dir/$1" ]; then echo "$dir/$1"; return; fi
  done
  echo "backup_db: $1 not found. Install postgresql client tools (brew install libpq)." >&2
  exit 1
}

case "$DATABASE_URL" in
  sqlite:*)
    DB_PATH="${DATABASE_URL#sqlite:///}"
    case "$DB_PATH" in ./*) DB_PATH="$ROOT/${DB_PATH#./}";; esac
    if [ ! -f "$DB_PATH" ]; then echo "backup_db: no database file at $DB_PATH" >&2; exit 1; fi
    OUT="$OUT_DIR/sl-$STAMP$LABEL.sqlite"
    if command -v sqlite3 >/dev/null 2>&1; then
      sqlite3 "$DB_PATH" ".backup '$OUT'"
    else
      cp "$DB_PATH" "$OUT"
    fi
    ;;
  postgres*|postgresql*)
    PG_URL="${DATABASE_URL/postgresql+psycopg:\/\//postgresql://}"
    PG_URL="${PG_URL/postgres+psycopg:\/\//postgresql://}"
    PG_DUMP="$(find_tool pg_dump)"
    OUT="$OUT_DIR/sl-$STAMP$LABEL.dump"
    "$PG_DUMP" --format=custom --no-owner --no-acl --file "$OUT" "$PG_URL"
    ;;
  *)
    echo "backup_db: DATABASE_URL must start with sqlite or postgresql" >&2
    exit 1
    ;;
esac

SIZE="$(wc -c < "$OUT" | tr -d ' ')"
echo "backup_db: wrote $OUT ($SIZE bytes)"
