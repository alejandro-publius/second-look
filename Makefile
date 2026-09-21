# Second Look. Every target prints what it proves. No em or en dashes anywhere.
SHELL := /bin/bash
.DEFAULT_GOAL := help
PY := uv run python
WEB := apps/web

.PHONY: render-readme help dev check lint types test web-build manifest-check dash-check verify-claims fhir-validate e2e smoke preflight submit-check poster deploy audit-verify

help:
	@echo "make dev | check | preflight | submit-check | fhir-validate | e2e | smoke | poster | deploy"

dev:
	@echo "API on :8000, web on :3000. Stop with Ctrl-C."
	@bash -c 'trap "kill 0" EXIT; $(PY) -m uvicorn apps.api.main:app --reload --port 8000 & (cd $(WEB) && npm run dev) & wait'

check: lint types test manifest-check dash-check verify-claims fhir-validate web-build
	@echo "CHECK GREEN"

lint:
	uv run ruff check .
	uv run ruff format --check .

types:
	uv run mypy core apps/api evals scripts

test:
	uv run pytest

web-build:
	@if [ -f $(WEB)/package.json ]; then cd $(WEB) && npm run build --silent && echo "web build ok"; else echo "no web app yet"; fi

manifest-check:
	$(PY) scripts/check_manifest.py

dash-check:
	$(PY) scripts/check_dashes.py

verify-claims:
	$(PY) scripts/verify_claims.py --synthetic

render-readme:
	$(PY) scripts/render_readme.py

fhir-validate:
	$(PY) scripts/fhir_validate.py

audit-verify:
	$(PY) scripts/verify_audit.py

e2e:
	cd $(WEB) && npx playwright test

smoke:
	$(PY) scripts/smoke.py

preflight:
	$(PY) scripts/preflight.py

submit-check:
	$(PY) scripts/submit_check.py

poster:
	cd $(WEB) && npm run poster

deploy:
	bash scripts/deploy.sh
