#!/usr/bin/env bash
# Back up the D1 study database to a private folder outside the repo.
#   bash scripts/backup_d1.sh              -> writes ~/second-look-backups/second-look-<stamp>.sql
#   BACKUP_DIR=/tmp/x bash scripts/backup_d1.sh
#
# It uses the wrangler login already on this Mac, so no GitHub secret is needed and no token is
# ever written down (Update 11D item 4). The dump lands outside the repo on purpose: it holds
# every answer people gave, and nothing with answers in it belongs in git.
#
# The GitHub workflow stays on manual. This is the backup that actually runs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="${D1_DATABASE:-second-look}"
OUT_DIR="${BACKUP_DIR:-$HOME/second-look-backups}"
KEEP="${BACKUP_KEEP:-30}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$OUT_DIR/$DB-$STAMP.sql"

mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

cd "$ROOT/worker"
npx --yes wrangler d1 export "$DB" --remote --output "$OUT" >/dev/null 2>&1 || {
  echo "backup-d1: wrangler export failed. Run 'npx wrangler login' and try again." >&2
  rm -f "$OUT"
  exit 1
}
[ -s "$OUT" ] || { echo "backup-d1: the export was empty, so nothing was kept" >&2; rm -f "$OUT"; exit 1; }
chmod 600 "$OUT"

# Keep the last KEEP dumps. Old answers are not more useful for being kept forever.
ls -1t "$OUT_DIR/$DB-"*.sql 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do rm -f "$old"; done

BYTES="$(wc -c <"$OUT" | tr -d ' ')"
printf '{\n  "generated_at_utc": "%s",\n  "script": "scripts/backup_d1.sh",\n  "database": "%s",\n  "file": "%s",\n  "bytes": %s\n}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$DB" "$OUT" "$BYTES" > "$OUT_DIR/last_backup.json"
chmod 600 "$OUT_DIR/last_backup.json"
echo "backup-d1: $OUT ($BYTES bytes)"
