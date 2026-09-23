#!/usr/bin/env bash
# UPDATE_14 section 8 item 2: make the repository public on Sep 30, in the one safe order.
#   bash scripts/go_public.sh          prints what it would do and changes nothing
#   bash scripts/go_public.sh --run    does it: on main, on Sep 30
# The steps live in scripts/go_public.py, which is tested (scripts/tests/test_go_public.py): it
# removes docs/internal, rewrites every mention left in a tracked file, stops unless make
# submit-check fails only on the repository not yet being public, and only then publishes.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-}" = "--run" ]; then
  exec uv run python scripts/go_public.py --yes
fi
exec uv run python scripts/go_public.py
