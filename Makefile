# Second Look. Every target prints what it proves. No em or en dashes anywhere.
SHELL := /bin/bash
.DEFAULT_GOAL := help
PY := uv run python
WEB := apps/web

.PHONY: export-records mcp render-readme help dev check lint types test web-build manifest-check dash-check design-check budget verify-claims fhir-validate e2e smoke preflight preflight-launch preflight-judges submit-check poster deploy audit-verify

help:
	@echo "make dev | check | preflight | submit-check | fhir-validate | e2e | smoke | poster | deploy"

dev:
	@echo "API on :8000, web on :3000. Stop with Ctrl-C."
	@bash -c 'trap "kill 0" EXIT; $(PY) -m uvicorn apps.api.main:app --reload --port 8000 & (cd $(WEB) && npm run dev) & wait'

check: lint types test manifest-check dash-check verify-claims fhir-validate web-build design-check
	@echo "CHECK GREEN"

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

dash-check:
	$(PY) scripts/check_dashes.py

# The look and feel gate from docs/updates/UPDATE_06.md section 6. Runs after web-build because
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

# The landing budgets from UPDATE_06 section 5 as Update 07 moved them. Needs the built app
# running on 3100, so it is not inside make check.
budget:
	cd $(WEB) && node scripts/budget.mjs

poster:
	cd $(WEB) && npm run poster

deploy:
	bash scripts/deploy.sh
