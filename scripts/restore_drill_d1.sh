#!/usr/bin/env bash
# Prove the backup restores: import the newest dump into a scratch D1 database, count what
# landed, compare it with the source, then delete the scratch database.
#   bash scripts/restore_drill_d1.sh
# Writes results/backup_drill.json. Never touches the production database (Update 11D item 4).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="${D1_DATABASE:-second-look}"
SCRATCH="${D1_SCRATCH:-second-look-restore-drill}"
OUT_DIR="${BACKUP_DIR:-$HOME/second-look-backups}"
FILE="${1:-$(ls -1t "$OUT_DIR/$DB-"*.sql 2>/dev/null | head -1)}"
[ -n "$FILE" ] && [ -s "$FILE" ] || { echo "restore-drill: no backup to restore" >&2; exit 1; }

cd "$ROOT/worker"
wr() { npx --yes wrangler "$@"; }

count() { # $1 database, $2 table -> the number of rows, or 0
  wr d1 execute "$1" --remote --json --command "SELECT COUNT(*) AS n FROM $2" 2>/dev/null \
    | tr -d ' \n' | sed -n 's/.*"n":\([0-9]*\).*/\1/p' | head -1
}

cleanup() { wr d1 delete "$SCRATCH" --skip-confirmation >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "restore-drill: restoring $(basename "$FILE") into scratch database $SCRATCH"
cleanup
wr d1 create "$SCRATCH" >/dev/null
wr d1 execute "$SCRATCH" --remote --file "$FILE" --yes >/dev/null

TABLES="arm_slot counter session response observer skeleton_ping"
ok=true
rows_json=""
for table in $TABLES; do
  src="$(count "$DB" "$table")"; src="${src:-0}"
  got="$(count "$SCRATCH" "$table")"; got="${got:-0}"
  [ "$src" = "$got" ] || ok=false
  printf -v rows_json '%s    "%s": { "source": %s, "restored": %s },\n' "$rows_json" "$table" "$src" "$got"
  echo "  $table: source $src, restored $got"
done

mkdir -p "$ROOT/results"
cat > "$ROOT/results/backup_drill.json" <<JSON
{
  "generated_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "script": "scripts/restore_drill_d1.sh",
  "database": "$DB",
  "scratch_database": "$SCRATCH",
  "backup_file": "$(basename "$FILE")",
  "backup_bytes": $(wc -c <"$FILE" | tr -d ' '),
  "restored": $ok,
  "tables": {
$(printf '%s' "$rows_json" | sed '$ s/,$//')
  },
  "note": "The scratch database is deleted at the end of the drill. Production is never touched."
}
JSON
$ok || { echo "restore-drill: row counts do not match" >&2; exit 1; }
echo "restore-drill: every table matched, results/backup_drill.json written"
