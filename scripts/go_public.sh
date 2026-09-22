#!/usr/bin/env bash
# UPDATE_14 section 8 item 2: the steps that make the repository public on Sep 30.
# By default this only prints what it would do. Alex runs it with --run, on main, on Sep 30.
set -euo pipefail
cd "$(dirname "$0")/.."

RUN=0
if [ "${1:-}" = "--run" ]; then RUN=1; fi

say() { printf '%s\n' "$*"; }
step() {
  say "  \$ $*"
  if [ "$RUN" = 1 ]; then eval "$@"; fi
}

if [ "$RUN" = 0 ]; then
  say "go-public: dry run. Nothing changes. Run 'bash scripts/go_public.sh --run' on Sep 30."
fi

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$RUN" = 1 ] && [ "$branch" != "main" ]; then
  say "go-public: refused, this is $branch. Check out main first."
  exit 1
fi

say "1. Remove the working notes between the team and their AI tools:"
step git rm -r -q docs/internal

say "2. Live files that still point at docs/internal (each must be fixed by hand before step 3):"
refs=$(git grep -l "docs/internal" -- . ':!docs/internal' 2>/dev/null || true)
if [ -n "$refs" ]; then printf '     %s\n' $refs; else say "     none"; fi
if [ "$RUN" = 1 ] && [ -n "$refs" ]; then
  say "go-public: stopped. Fix the references above, commit, and run again."
  exit 1
fi

say "3. The submission gate. Only repo_public may fail here:"
step uv run python scripts/submit_check.py "|| true"

say "4. Commit and push the removal:"
step git commit -q -m "'Go public: working notes removed from the published tree'"
step git push -q origin main

say "5. Make the repository public:"
step gh repo edit alejandro-publius/second-look --visibility public --accept-visibility-change-consequences

say "6. Check the gate once more; it must pass:"
step uv run python scripts/submit_check.py
