# Second Look. Every target prints what it proves. No em or en dashes anywhere.
SHELL := /bin/bash
.DEFAULT_GOAL := help
PY := uv run python
WEB := apps/web

.PHONY: video-clips video-rough go-public judge-check diagrams readability worker-e2e worker-check deploy-preview new-city export-records mcp render-readme help dev check lint types test web-build manifest-check dash-check design-check budget verify-claims fhir-validate e2e smoke preflight preflight-launch preflight-judges submit-check poster deploy audit-verify

help:
	@echo "make dev | check | preflight | submit-check | fhir-validate | e2e | smoke | poster | deploy"

dev:
	@echo "API on :8000, web on :3000. Stop with Ctrl-C."
	@bash -c 'trap "kill 0" EXIT; $(PY) -m uvicorn apps.api.main:app --reload --port 8000 & (cd $(WEB) && npm run dev) & wait'

check: lint types test manifest-check dash-check readability diagrams verify-claims worker-check fhir-validate web-build design-check
	@echo "CHECK GREEN"

# Update 10 answer A3. Python is the reference: it writes worker/src/content.json and the golden
# vectors in worker/golden; the TypeScript ports must reproduce every vector. The emitter's
# Bundles land in fhir/build/instances, so fhir-validate, which runs next, checks them too.
worker-check:
	$(PY) scripts/build_worker_content.py --check
	$(PY) evals/golden_vectors.py --check
	cd worker && npm run typecheck --silent && npm test --silent

# The Worker end to end: wrangler dev with a local D1 and KV, the schema and the arms applied,
# rain answered by a stub on this machine, every judge facing route driven over HTTP. About a
# minute, so it is its own target and a CI step rather than part of make check.
worker-e2e:
	cd worker && npm run e2e

lint:
	uv run ruff check .
	uv run ruff format --check .

types:
	uv run mypy core apps/api apps/mcp evals scripts

test:
	uv run pytest

web-build:
	@if [ -f $(WEB)/package.json ]; then cd $(WEB) && npm run build --silent && echo "web build ok"; else echo "no web app yet"; fi

manifest-check:
	$(PY) scripts/check_manifest.py

# Hard rule 18 as a gate, not an intention: plain words at a reading age of about 12, measured
# on every string a person can see. The exceptions list is content/readability_exceptions.yaml
# and it is meant to stay short.
readability:
	$(PY) scripts/check_readability.py

# Every Mermaid block in README.md and docs/ parses. A broken diagram renders as nothing on
# GitHub and nobody notices until a judge opens the page. MERMAID_CLI=1 also renders each one.
diagrams:
	$(PY) scripts/check_diagrams.py

dash-check:
	$(PY) scripts/check_dashes.py

# The look and feel gate from docs/internal/updates/UPDATE_06.md section 6. Runs after web-build because
# the tap target measurement drives the built app on the phone viewport.
design-check:
	cd $(WEB) && node scripts/design-check.mjs

verify-claims:
	$(PY) scripts/verify_claims.py --synthetic

render-readme:
	$(PY) scripts/render_readme.py

fhir-validate:
	$(PY) scripts/fhir_validate.py

audit-verify:
	$(PY) scripts/verify_audit.py

# The read only MCP server over our records (Update 10 tier 2 item 2). Local, over stdio.
# make export-records writes data/export from the local database; make mcp serves it.
export-records:
	$(PY) scripts/export_records.py --out data/export

mcp:
	$(PY) -m apps.mcp.server --export data/export

# A follower city in one command (Update 10 tier 2 item 3): a region pack stub, the nested
# Locations in FSH inside their guide, a poster and the five step checklist. No claims are made.
#   make new-city NAME=Heraklion COUNTRY=Greece LAT=35.3387 LON=25.1442
new-city:
	@test -n "$(NAME)" || { echo "make new-city NAME=<city> COUNTRY=<country> LAT=<lat> LON=<lon>"; exit 1; }
	$(PY) scripts/new_city.py --name "$(NAME)" --country "$(COUNTRY)" --lat $(LAT) --lon $(LON)

e2e:
	cd $(WEB) && npm run build --silent && npx playwright test

smoke:
	$(PY) scripts/smoke.py

preflight:
	$(PY) scripts/preflight.py

# Update 11 section 1. preflight-launch gates only what the two minute test uses, so the creek
# check form and the health sentences cannot hold up Wednesday. preflight-judges is the rest.
preflight-launch:
	$(PY) scripts/preflight.py --gate launch

preflight-judges:
	$(PY) scripts/preflight.py --gate judges

submit-check:
	$(PY) scripts/submit_check.py

# Update 14 section 7. Screen recordings (needs the built app on 3100), then the rough cut with a
# scratch voice. Nothing either writes is committed: they are video files.
video-clips:
	cd $(WEB) && node scripts/record-clips.mjs

video-rough:
	$(PY) scripts/video_rough.py

# Update 14 section 8 item 2. Says what it would do; with GO=yes, on main on Sep 30, removes the
# working notes, runs submit-check, and only then makes the repository public.
go-public:
	$(PY) scripts/go_public.py $(if $(filter yes,$(GO)),--yes,)

# The one command for a judge: no key, no network, five lines out. Tests, FHIR validation,
# the web build and the design gate, the audit chain, and a scan for secrets.
judge-check:
	$(PY) scripts/judge_check.py

# The landing budgets from UPDATE_06 section 5 as Update 07 moved them. Needs the built app
# running on 3100, so it is not inside make check.
budget:
	cd $(WEB) && node scripts/budget.mjs

backup:
	bash scripts/backup_d1.sh

restore-drill:
	bash scripts/restore_drill_d1.sh

backup-install:
	bash scripts/install_backup_job.sh

poster:
	cd $(WEB) && npm run poster

deploy:
	bash scripts/deploy.sh

# The depth branch's own preview on Cloudflare Pages (Update 10 rule B and answer A1). The export
# is built with an empty API origin, so the browser talks to one origin and the API is reached
# through /api/* by the Pages Function and the service binding in apps/web/wrangler.jsonc. This
# never touches production: production deploys come from main only.
PREVIEW_URL := https://depth.second-look-79t.pages.dev
deploy-preview:
	$(PY) scripts/build_walks.py --clips-only
	cd $(WEB) && NEXT_PUBLIC_API_ORIGIN="" NEXT_PUBLIC_SITE_URL=$(PREVIEW_URL) NEXT_PUBLIC_BUILD_HASH=$$(git rev-parse --short HEAD) npm run export
	cd $(WEB) && npx wrangler pages deploy out --project-name second-look --branch depth --commit-dirty=true
	@echo "preview at $(PREVIEW_URL); check with: curl -sI $(PREVIEW_URL)/health"
