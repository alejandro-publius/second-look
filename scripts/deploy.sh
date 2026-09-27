#!/usr/bin/env bash
# Production deploys, Cloudflare only, from main only (Update 10 rule B, Update 10C answer 2).
#
#   bash scripts/deploy.sh worker   apply the additive D1 tables, then deploy the API Worker
#   bash scripts/deploy.sh web      build the static export with the API on the same origin and
#                                   deploy it to the Pages project's production branch
#
# The order at the merge after data lock is: worker, then the study contract tests and the phone
# tests against production, then web, then the phone tests again (docs/notes/hosting.md). Needs
# `npx wrangler whoami` to show the account; nothing here asks for a card.
#
# After each deploy scripts/deploy_record.py writes a row into the deploy record in
# docs/notes/hosting.md: the Worker's version id, or the Pages deployment's id with a copy of the
# exact files that went up, which is what make rollback needs. Once the phone tests pass, mark the
# rows good with `uv run python scripts/deploy_record.py good` and commit the record.
set -euo pipefail
cd "$(dirname "$0")/.."
WHAT="${1:-}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "main" ] && [ "${ALLOW_BRANCH:-}" != "yes" ]; then
  echo "deploy: production deploys come from main only (you are on $BRANCH). Set ALLOW_BRANCH=yes to override on purpose." >&2
  exit 1
fi
case "$WHAT" in
  worker)
    (cd worker && npx wrangler d1 execute second-look --remote --file schema.sql)
    # UPDATE_32: CREATE TABLE IF NOT EXISTS cannot add a column to a table that is already there, so
    # the visit table's language column is added once, only when the live table lacks it, and
    # before the Worker that writes it goes up.
    cols="$(cd worker && npx wrangler d1 execute second-look --remote --json --command "SELECT name FROM pragma_table_info('visit')")"
    if ! printf '%s' "$cols" | uv run python -c 'import json,sys; sys.exit(0 if any(r.get("name") == "language" for b in json.load(sys.stdin) for r in b.get("results", [])) else 1)'; then
      (cd worker && npx wrangler d1 execute second-look --remote --file migrations/0001_visit_language.sql)
    fi
    printed="$(mktemp)"
    (cd worker && npx wrangler deploy) | tee "$printed"
    uv run python scripts/deploy_record.py record worker --output-file "$printed"
    rm -f "$printed"
    echo "deploy: worker live; now run the study contract tests and the phone tests against production"
    ;;
  web)
    # The walk clips are never committed; cut them from the cache, and refuse to ship without them.
    uv run python scripts/build_walks.py --clips-only
    (cd apps/web && NEXT_PUBLIC_API_ORIGIN="" NEXT_PUBLIC_SITE_URL="https://second-look-79t.pages.dev" NEXT_PUBLIC_BUILD_HASH="$(git rev-parse --short HEAD)" npm run export)
    printed="$(mktemp)"
    (cd apps/web && npx wrangler pages deploy out --project-name second-look --branch main --commit-dirty=true) | tee "$printed"
    uv run python scripts/deploy_record.py record web --output-file "$printed" --web-dir apps/web
    rm -f "$printed"
    echo "deploy: web live at https://second-look-79t.pages.dev; run the phone tests again and check /health through the Pages origin"
    ;;
  *)
    echo "usage: bash scripts/deploy.sh worker | web" >&2
    exit 2
    ;;
esac
