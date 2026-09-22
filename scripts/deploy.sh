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
    (cd worker && npx wrangler deploy)
    echo "deploy: worker live; now run the study contract tests and the phone tests against production"
    ;;
  web)
    (cd apps/web && NEXT_PUBLIC_API_ORIGIN="" NEXT_PUBLIC_SITE_URL="https://second-look-79t.pages.dev" NEXT_PUBLIC_BUILD_HASH="$(git rev-parse --short HEAD)" npm run export)
    (cd apps/web && npx wrangler pages deploy out --project-name second-look --branch main --commit-dirty=true)
    echo "deploy: web live at https://second-look-79t.pages.dev; run the phone tests again and check /health through the Pages origin"
    ;;
  *)
    echo "usage: bash scripts/deploy.sh worker | web" >&2
    exit 2
    ;;
esac
