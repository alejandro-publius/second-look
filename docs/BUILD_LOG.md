# Build log

Five lines per phase: what, proof, surprises, decisions, next.

## Phase 0, workspace, 2026-09-20 21:40Z
- What: uv project on Python 3.12, Makefile with every target named in the updates, GitHub Actions job (uv, Node 20, Java 17, FHIR cache), Next.js 16 app stripped to system fonts and no vendor assets, dash checker, manifest checker, verify_claims stage 1, the UTC lock constant with tests one second either side, README and doc stubs, UPDATE_04 saved.
- Proof: `make check` printed CHECK GREEN (ruff, mypy, 5 tests, manifest 0 images, dash-check clean, 0 claims, no instances to validate, web build static).
- Surprises: Vercel and Fly CLIs are not installed, so P1 goes through docker compose. Update 03 was never pasted, so P1, P2, P3, K6 and F2 follow Update 04's own wording. create-next-app now drops AGENTS.md and CLAUDE.md into apps/web; kept, they only point at Next.js docs.
- Decisions: compose runs Postgres as the update requires, SQLite stays the local default. Java 17 via Homebrew for the validator. Validator pinned to the release downloaded today (fhir/tools/VALIDATOR_VERSION).
- Next: Phase 1, P2 first: our FSH examples inside a copy of their guide at b907cf0, then the validator verdict.

## Phase 1, proofs, 2026-09-20 21:45Z
- What: P2 built our FSH (CodeSystem, two ValueSets, two Questionnaires, one complete visit Bundle for Strawberry Creek) inside a copy of hl7-eu/oah at b907cf0 and ran the pinned HL7 validator 6.10.4. P1 stood up Postgres, the API and the web app with docker compose and a smoke test. K6 wrote one tagged Location to the shared sandbox and removed it by id.
- Proof: `make fhir-validate` printed 0 errors, 15 warnings (14 narrative best practice, 1 UCUM unit unverifiable with terminology off); `scripts/smoke.py` printed landing 200 in 131 ms, api health ok, db rows 1 then 2; `scripts/sandbox_write_test.sh` printed 201, 200, 200, 410.
- Surprises: the only validator errors were mine, UI labels placed in coding displays; their preferred binding on Observation.code accepts our local codes with an information note, exactly as hoped. Java 17 came from Homebrew in two minutes.
- Decisions: their codes for values and categories, ours for the four feature codes; F2 not needed; the mirror goes ahead behind a flag.
- Next: Phase 2, contracts first, then W1 to W7 in parallel.

## Phase 2 prep, foundation for parallel work, 2026-09-20 22:30Z
- What: docs/CONTRACTS.md (folder ownership, shared shapes, API and export schemas, results and audit conventions), core/records.py, core/content_loader.py with every fail-loud check, content files (4 features, 24 form items mirroring the official app with every item unverified, 16 test items, follow-up rules, empty approved sentences, locale strings), 40 labelled gray placeholders with manifest rows, docs/analysis_plan.md with the eight amendments folded in, project made installable so scripts import core.
- Proof: `make check` CHECK GREEN; the loader reports 40 photos, 16 test items and 89 missing human inputs, which is what preflight will fail on.
- Surprises: an in-memory SQLite test database needs a static pool or each request sees an empty database. Scripts could not import core until the project became a package. The Next.js generator writes an AGENTS.md with em dashes; replaced.
- Decisions: the app's "Which ones?" free text becomes a pick list from the region pack plus Not sure, so no free text is stored; subagents never commit and never edit pyproject.
- Next: spawn W1 to W7 in parallel on their folders.

## Phase 2, parallel build, 2026-09-21 00:40Z
- What: seven workstreams built and integrated on placeholders. W1 the study and creek check API with migrations, privacy guards and backup and restore. W2 the pre-registered analysis, synthetic scenarios, power, consensus and the example picker. W3 the FHIR emitter, goldens, store, routes, sandbox mirror and guide proposal. W5 the gate, follow-ups, rainfall, labels and health card. W6 the model sweep, benchmark, ablation and the checker. W7a the audit log, photo tools and the launch and submission gates. W7b the sourced drafts, human packs and the README. W4 the web app is still running.
- Proof: `make check` CHECK GREEN; 488 tests pass; `uv run python scripts/preflight.py` prints "preflight: 114 failed, of which 114 need a human", so nothing is left that we can fix ourselves; `uv run python scripts/verify_claims.py --synthetic` checks 19 claims against results/; `JAVA17_HOME=... scripts/fhir_validate.py` 0 errors on three files.
- Surprises: two API billing outages stopped every agent twice, so they were resumed in a staggered order. A Hypothesis property test caught a real defect: adding equal weights in a different order left a speck instead of zero, so a tied scored vote read as decisive. On synthetic equal-skill data the scored consensus vote loses to the plain vote, which makes the README sentence conditional. HAPI rejects the bare conditional create form, so transactions use Type?params. The check Questionnaire in the guide is now generated from content/form.yaml with a test against drift.
- Decisions: fake model runs write cost_log_fake.jsonl; the checker refuses to flag from a synthetic pass table; every stored record appends a record_written audit line; tests never touch the real audit chain.
- Next: Phase 3 integration on docker compose, then the adversarial review.
