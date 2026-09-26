#!/usr/bin/env bash
# UPDATE_30 section 8: make the repository public on Sep 30, in the one safe order.
#   bash scripts/go_public.sh          prints what it would do and changes nothing
#   bash scripts/go_public.sh --dry    every step before the flip, in a throwaway worktree
#   bash scripts/go_public.sh --run    does it all: on main, on Sep 30
# The steps live in scripts/go_public.py, which is tested (scripts/tests/test_go_public.py). The
# same as make go-public, make go-public GO=dry (--no-flip) and make go-public GO=yes.
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
  --run) exec uv run python scripts/go_public.py --yes ;;
  --dry) exec uv run python scripts/go_public.py --no-flip ;;
esac
exec uv run python scripts/go_public.py
