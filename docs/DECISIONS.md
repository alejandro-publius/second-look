# Decisions

One line each, dated, with the reason. Newest at the bottom.

- 2026-09-20: PLAN.md v2 decisions stand (Vercel plus Fly, CI pins, their codes where they exist, CodeableConcept values, UTC lock constant). See PLAN.md.
- 2026-09-20: Update 03 was never pasted into this terminal. P1, P2, P3, K6 and fallback F2 are built from Update 04's own descriptions of them. Update 03 should be pasted so this can be checked.
- 2026-09-20: docker compose runs Postgres, as Update 04 section 3 W1 and Phase 3 require. SQLite stays the zero-config local default through DATABASE_URL.
- 2026-09-20: Vercel and Fly CLIs are not installed or logged in, so P1 is proved with docker compose and `make deploy` is left as one command.
- 2026-09-20: No .env exists, so every model call in this run uses the fake client. The P3 probe is skipped.
- 2026-09-20: P2 passed (0 errors against their profiles at b907cf0), so the FHIR workstream uses their LocationOah and ObservationIndicatorsOah profiles. Fallback F2 is not taken. Their codes for values and categories, ours for feature codes; see docs/fhir_mapping.md.
- 2026-09-20: K6 passed, so the sandbox mirror is built as planned, still behind SANDBOX_MIRROR_ENABLED and the ledger.
- 2026-09-20: Subagents do not commit or edit pyproject.toml; the integrator commits per workstream after review, so the history stays linear and honest.
