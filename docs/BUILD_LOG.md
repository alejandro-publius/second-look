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
