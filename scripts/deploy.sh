#!/usr/bin/env bash
# One command deploy. Needs `fly auth login` and `vercel login` done once by Alex.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v fly >/dev/null || { echo "install flyctl: brew install flyctl, then fly auth login"; exit 1; }
command -v vercel >/dev/null || { echo "install vercel: npm i -g vercel, then vercel login"; exit 1; }
: "${DATABASE_URL:?set DATABASE_URL to the Neon or Fly Postgres url}"
fly apps list | grep -q second-look-api || fly apps create second-look-api
fly secrets set DATABASE_URL="$DATABASE_URL" EXPORT_TOKEN="${EXPORT_TOKEN:-$(openssl rand -hex 24)}" QA_KEY="${QA_KEY:-$(openssl rand -hex 24)}" >/dev/null
fly deploy --remote-only
API_URL="https://$(fly status --json | python3 -c 'import sys,json; print(json.load(sys.stdin)["Hostname"])')"
( cd apps/web && vercel --prod --yes -e NEXT_PUBLIC_API_ORIGIN="$API_URL" )
echo "deployed api at $API_URL; web url printed above"
