#!/usr/bin/env bash
# The scheduled sandbox re-push (Update 14 section 6 item 3), run by launchd at 08:00 on Sep 28,
# Sep 30 and Oct 1. Anyone can delete records on the shared sandbox, so our worked visit and our
# Library entry are put back by conditional create, which is a no-op for what is still there.
# Two-minute test sessions are never mirrored; the script only takes visit Bundles.
set -euo pipefail
cd "$(dirname "$0")/.."
today="$(date +%Y-%m-%d)"
case "$today" in
  2026-09-28|2026-09-30|2026-10-01) ;;
  *) echo "$(date -u +%FT%TZ) repush: $today is not a scheduled day, nothing sent"; exit 0 ;;
esac
echo "$(date -u +%FT%TZ) repush: start on $(git rev-parse --abbrev-ref HEAD) at $(git rev-parse --short HEAD)"
SANDBOX_MIRROR_ENABLED=true uv run python scripts/repush_sandbox.py \
  --bundle fhir/golden/visit-strawberry-creek-1.json --library
echo "$(date -u +%FT%TZ) repush: done"
