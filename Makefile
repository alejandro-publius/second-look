# Second Look. Every target prints what it proves. No em or en dashes anywhere.
SHELL := /bin/bash
.DEFAULT_GOAL := help
PY := uv run python
WEB := apps/web

.PHONY: precache-budget report-pdf panel-status done-check coverage-core demo-open-check test-counts demo-offline consensus-coarseness consensus-check ai-run video-clips video-rough go-public judge-check diagrams diagrams-render readability worker-e2e worker-check deploy-preview new-city export-records mcp render-readme help dev check lint types test web-build manifest-check dash-check design-check budget verify-claims fhir-validate e2e smoke preflight preflight-launch preflight-judges submit-check poster deploy audit-verify reproduce mutation

help:
	@echo "make dev | check | preflight | submit-check | fhir-validate | e2e | smoke | poster | deploy"

# npm run dev serves the site on 3100, so the API is told that origin, or the browser's calls fail
# CORS. The audit log line each stored check writes goes under data/, never to the tracked
# audit/log.jsonl. make demo-offline below is the same with seeded data and no network.
dev:
	@echo "API on :8000, web on http://localhost:3100. Stop with Ctrl-C."
	@bash -c 'trap "kill 0" EXIT; PUBLIC_WEB_ORIGIN=http://localhost:3100 AUDIT_LOG_PATH=$(CURDIR)/data/dev_audit.jsonl $(PY) -m uvicorn apps.api.main:app --reload --port 8000 & (cd $(WEB) && npm run dev) & wait'

# The site and the API on this machine with no network and no key, on seeded demo data (UPDATE_27
# block 24). scripts/seed_demo.py fills data/demo through the API's own routes with every socket
# to another machine refused, and fails if one was tried. Then the API serves that folder and the
# site runs in dev mode against it. Neither process gets a key; their proxy goes nowhere; the QA
# key and the export token are empty, so nothing can be marked or exported. Needs one `uv sync`
# and one `npm ci` in apps/web beforehand, which are the only steps that use the network.
DEMO_DIR := $(CURDIR)/data/demo
DEMO_API_PORT ?= 8000
DEMO_WEB_PORT ?= 3100
DEMO_ENV := ANTHROPIC_API_KEY= DATABASE_URL=sqlite:///$(DEMO_DIR)/demo.db FHIR_STORE_DIR=$(DEMO_DIR)/fhir_store UPLOAD_DIR=$(DEMO_DIR)/uploads AUDIT_LOG_PATH=$(DEMO_DIR)/audit.jsonl SANDBOX_CACHE_DIR=$(DEMO_DIR)/sandbox_cache QA_KEY= EXPORT_TOKEN= PUBLIC_WEB_ORIGIN=http://localhost:$(DEMO_WEB_PORT) HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 NEXT_TELEMETRY_DISABLED=1
demo-offline:
	env -u ANTHROPIC_API_KEY uv run --offline python scripts/seed_demo.py --out $(DEMO_DIR)
	@echo "demo-offline: API on :$(DEMO_API_PORT), site on http://localhost:$(DEMO_WEB_PORT)/city?creek=strawberry-creek. Stop with Ctrl-C."
	@bash -c 'trap "kill 0" EXIT; env $(DEMO_ENV) uv run --offline python -m uvicorn apps.api.main:app --port $(DEMO_API_PORT) & (cd $(WEB) && node scripts/build-content.mjs && env $(DEMO_ENV) NEXT_PUBLIC_API_ORIGIN=http://localhost:$(DEMO_API_PORT) npx next dev -p $(DEMO_WEB_PORT)) & wait'

check: lint types test manifest-check dash-check readability diagrams verify-claims consensus-check worker-check fhir-validate web-build design-check
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
	@if [ -f $(WEB)/package.json ]; then cd $(WEB) && npm run build --silent && echo "web build ok" && node scripts/check-bundle.mjs && node scripts/check-preloads.mjs; else echo "no web app yet"; fi

manifest-check:
	$(PY) scripts/check_manifest.py

# Hard rule 18 as a gate, not an intention: plain words at a reading age of about 12, measured
# on every string a person can see. The exceptions list is content/readability_exceptions.yaml
# and it is meant to stay short.
readability:
	$(PY) scripts/check_readability.py

# Every Mermaid block in README.md and docs/ parses. A broken diagram renders as nothing on
# GitHub and nobody notices until a judge opens the page. MERMAID_CLI=1 also renders each one.
# The three diagrams in docs/diagrams (UPDATE_27 block 23) are .mmd sources drawn as SVGs by the
# Mermaid CLI pinned in tools/diagrams, in the Chromium Playwright installs for apps/web, so it
# needs `(cd tools/diagrams && npm ci)` once. make diagrams renders each source again and fails
# when a render fails or a committed SVG is missing, stale or edited by hand; make
# diagrams-render draws them after an edit. tools/diagrams/render.mjs says why the comparison is
# by content across machines and by bytes on the one that drew them.
DIAGRAM_TOOL := tools/diagrams

diagrams:
	$(PY) scripts/check_diagrams.py
	@test -d $(DIAGRAM_TOOL)/node_modules || { echo "diagrams: run (cd $(DIAGRAM_TOOL) && npm ci) first"; exit 1; }
	cd $(DIAGRAM_TOOL) && node --test render.test.mjs && node render.mjs --check

diagrams-render:
	@test -d $(DIAGRAM_TOOL)/node_modules || { echo "diagrams: run (cd $(DIAGRAM_TOOL) && npm ci) first"; exit 1; }
	cd $(DIAGRAM_TOOL) && node render.mjs

dash-check:
	$(PY) scripts/check_dashes.py

# The look and feel gate from docs/internal/updates/UPDATE_06.md section 6. Runs after web-build because
# the tap target measurement drives the built app on the phone viewport.
design-check:
	cd $(WEB) && node scripts/design-check.mjs

verify-claims:
	$(PY) scripts/verify_claims.py --synthetic
	$(PY) scripts/verify_claims.py --file docs/devpost.md
	$(PY) scripts/verify_claims.py --file docs/submission/JUDGE_QA.md
	$(PY) scripts/api_inventory.py --check
	$(PY) scripts/verify_claims.py --file docs/API.md
	$(PY) scripts/verify_claims.py --file docs/MCP.md
	$(PY) scripts/verify_claims.py --file WRITEUP.md
	$(PY) scripts/verify_claims.py --file SECURITY.md
	$(PY) scripts/verify_claims.py --file DEPLOY.md
	$(PY) scripts/verify_claims.py --file docs/DATA_CARD.md
	$(PY) scripts/verify_claims.py --file docs/MODEL_CARD.md
	$(PY) scripts/verify_claims.py --file docs/THREAT_MODEL.md
	$(PY) scripts/verify_claims.py --file docs/ACCEPTANCE.md

# The README and every other doc whose numbers verify-claims checks, so a new result or a new
# test count is written everywhere it is quoted, not only in the README.
RENDERED_DOCS := WRITEUP.md SECURITY.md DEPLOY.md docs/API.md docs/MCP.md docs/DATA_CARD.md docs/MODEL_CARD.md docs/THREAT_MODEL.md docs/ACCEPTANCE.md
render-readme:
	$(PY) scripts/render_readme.py
	@for doc in $(RENDERED_DOCS); do $(PY) scripts/render_readme.py --readme $$doc || exit 1; done

# UPDATE_29 section 5: docs/REPORT.pdf, a technical report of about six pages, from the README,
# the docs it names and results/. docs/report/source.md holds its own words and names each
# section it takes. Needs pandoc at the version pinned in scripts/build_report.py and apps/web's
# node_modules with Playwright's Chromium; no network. It writes the stamp results/report_pdf.json,
# and scripts/tests/test_report_pdf.py fails in make check when the PDF is older than its sources.
report-pdf:
	$(PY) scripts/build_report.py

# The test counts the README cites (UPDATE_27 block 24): Python tests, Worker golden cases,
# Playwright tests and the Worker e2e sections, into results/test_counts.json. Not in make check,
# because every branch that adds a test would turn it red; run it last, before render-readme.
test-counts:
	$(PY) scripts/count_tests.py

# UPDATE_22 section 1 answer 1: can four photos per feature weight a group's votes? A synthetic
# simulation, about 15 seconds. It writes results/consensus_coarseness.json and the table
# results/consensus_coarseness.md. consensus-check runs it again and fails unless both committed
# files are exactly what it writes, so the README's numbers from that file cannot go stale.
consensus-coarseness:
	$(PY) evals/consensus_coarseness.py

consensus-check:
	$(PY) evals/consensus_coarseness.py --check

fhir-validate:
	$(PY) scripts/fhir_validate.py

audit-verify:
	$(PY) scripts/verify_audit.py

# Hard rule 14 on every commit, not only at submission: `check: secrets` below makes it part of
# make check. gitleaks reads the history of the checked out commit, where each fake value is
# named in .gitleaksignore with its reason, then the submit-check scan reads every file git
# would commit. CI installs gitleaks 8.30.1; on a Mac, brew install gitleaks.
.PHONY: secrets
check: secrets
secrets:
	@command -v gitleaks >/dev/null || { echo "secrets: gitleaks is not installed; brew install gitleaks"; exit 1; }
	gitleaks git . --log-opts=HEAD --redact --no-banner --exit-code 1
	$(PY) scripts/submit_check.py --secrets-only

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

# UPDATE_27 sections 0 and 3: the definition of done. Runs the command of every item in
# docs/internal/DONE.md and prints PASS, RED, BLOCKED or HUMAN per item, then the line
# "RED: <n> BLOCKED: <n> HUMAN: <n>". Red until the work is done, so it is not part of make check.
# The panel study (docs/internal/PANEL_STUDY.md): completed sessions by source and arm, live.
panel-status:
	$(PY) scripts/panel_status.py

done-check:
	$(PY) scripts/done_check.py

# A done-check item: line and branch coverage of core/ by core's own tests, 90 percent or red.
# The data file stays outside the repo. About a minute.
coverage-core:
	COVERAGE_FILE=$${TMPDIR:-/tmp}/second-look-coverage-core uv run --with pytest-cov pytest core --cov=core --cov-config=scripts/coverage_core.ini --cov-fail-under=90 --cov-report=term:skip-covered

# A dated done-check item: the live /demo shows judge mode open. GET requests only.
demo-open-check:
	cd $(WEB) && node scripts/demo-open-check.mjs

# The paid model run, in one command, for Alex once the model gate flags are flipped and the key
# is in .env (docs/ALEX_TODO.md step 2). Batch API throughout. The 16-photo sweep refuses above 10
# dollars worst case and the footage run above 25 expected, inside the 40 dollar cap of Update 14.
# Afterwards the walks are gated again on the real answers and the pool numbers rewritten; the
# README's AI table is filled by the next session from results/, never by hand.
ai-run:
	$(PY) evals/model_sweep.py --real --max-usd 60
	$(PY) evals/benchmark.py --real --runs 3
	$(PY) evals/footage.py --real --max-usd 120
	$(PY) scripts/build_walks.py --no-clips
	$(PY) evals/footage_pool.py

# Update 14 section 7. Screen recordings (needs the built app on 3100), then the rough cut with a
# scratch voice. Nothing either writes is committed: they are video files.
video-clips:
	@mkdir -p docs/video/clips
	uv run --with markdown python -c "import markdown,pathlib; r=pathlib.Path('.').resolve(); h=markdown.markdown(pathlib.Path('README.md').read_text(), extensions=['tables','fenced_code','toc']); pathlib.Path('docs/video/clips/readme.html').write_text('<!doctype html><meta charset=utf-8><base href=\"file://'+str(r)+'/\"><style>body{font:18px/1.5 -apple-system,sans-serif;max-width:980px;margin:40px auto;padding:0 24px}img{max-width:100%}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px}</style>'+h)"
	cd $(WEB) && README_HTML=$(CURDIR)/docs/video/clips/readme.html node scripts/record-clips.mjs

video-rough:
	$(PY) scripts/video_rough.py

# Update 14 section 8 item 2. Says what it would do; with GO=yes, on main on Sep 30, removes the
# working notes, runs submit-check, and only then makes the repository public.
go-public:
	$(PY) scripts/go_public.py $(if $(filter yes,$(GO)),--yes,)
# bash scripts/go_public.sh --run does the same thing; Alex was told that command first.

# The one command for a judge: no key, no network, six lines out. Tests, every AI number graded
# again from the raw replies, FHIR validation, the web build and the design gate, the audit chain,
# and a scan for secrets.
judge-check:  # its second step is make reproduce
	$(PY) scripts/judge_check.py

# UPDATE_29 section 4 item 2: mutmut changes the gate, the follow-up selector, scoring and the FHIR
# emitter one small change at a time, and core's own tests must catch each change: 85 percent or
# more per module, written to results/mutation.json. About three minutes, so not in make check.
mutation:
	$(PY) scripts/mutation.py

# UPDATE_29 section 4: every AI number in results/ graded again from the raw model replies of the
# paid runs in evals/fixtures/raw/, and every synthetic result made again from its seed, by the
# same code the runs ran. No key, and no network: every socket to another machine is refused.
# Fails if any committed number differs. About half a minute.
reproduce:
	env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN uv run --offline python evals/reproduce.py

# The landing budgets from UPDATE_06 section 5 as Update 07 moved them. Needs the built app
# running on 3100, so it is not inside make check.
budget:
	cd $(WEB) && node scripts/budget.mjs

# UPDATE_30 section 1 item 1: what a first visit downloads in the background. The two tests in
# apps/web/tests/offline-budget.spec.ts run against this checkout's production build on 3100, the
# first writing its measurement to results/precache_budget.json, and fail above 3 MB or if the
# test stops working offline. make e2e runs the same tests without writing the file.
precache-budget:
	cd $(WEB) && PRECACHE_BUDGET_OUT=$(CURDIR)/results/precache_budget.json npx playwright test tests/offline-budget.spec.ts

backup:
	bash scripts/backup_d1.sh

restore-drill:
	bash scripts/restore_drill_d1.sh

backup-install:
	bash scripts/install_backup_job.sh

poster:
	cd $(WEB) && npm run poster

# UPDATE_27 block 23: the README gallery, the GIF of the two-minute test and the social preview.
# The read only pages come from the live site, reading only (apps/web/scripts/gallery-guard.mjs
# refuses anything that could write). The test flow and the sample record come from this
# checkout's production build on port GALLERY_PORT with the mock API, so nothing is sent anywhere.
# Needs the network and a few minutes, so it is not part of make check; scripts/tests/
# test_gallery.py checks what it wrote on every make check.
GALLERY_PORT ?= 3217
.PHONY: screens
screens:
	@if curl -s -o /dev/null http://127.0.0.1:$(GALLERY_PORT)/; then echo "screens: port $(GALLERY_PORT) is in use; set GALLERY_PORT"; exit 1; fi
	cd $(WEB) && npm run build --silent
	@bash -c 'set -euo pipefail; cd $(WEB); node node_modules/next/dist/bin/next start -p $(GALLERY_PORT) >/dev/null 2>&1 & server=$$!; trap "kill $$server 2>/dev/null || true" EXIT; for i in $$(seq 1 60); do curl -fs -o /dev/null http://127.0.0.1:$(GALLERY_PORT)/ && break; sleep 1; done; GALLERY_LOCAL_URL=http://127.0.0.1:$(GALLERY_PORT) node scripts/gallery.mjs'
	$(PY) scripts/make_gallery.py
	uv run pytest -q scripts/tests/test_gallery.py

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
