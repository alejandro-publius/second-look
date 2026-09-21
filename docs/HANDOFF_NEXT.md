# Handoff: where Second Look stands, 2026-09-21 01:30Z

Repo `~/second-look`, private, `alejandro-publius/second-look`, branch main, commit 138751d.
Read CLAUDE.md, then PLAN.md, then only the brief section a session names.

## Workstreams

| Line | State |
|---|---|
| W1 API and data | Done. Study and creek check endpoints, alembic on SQLite and Postgres, rate limit, hidden field, CSP, no addresses in logs, backup and restore with a drill. |
| W2 Analysis | Done. The plan implemented exactly, five synthetic scenarios, bootstrap and permutation, power, consensus, example picker. Refuses real data before the lock or without the tag. |
| W3 FHIR | Done. Emitter, goldens, store, routes, sandbox mirror script, Postman, guide proposal. |
| W4 Web | Done. Landing, test flow, judge mode, creek check with offline queue, record with View as FHIR, two observer screen, quick check, poster, about, privacy, how we know. 28 Playwright tests, axe clean on nine screens. |
| W5 Core | Done. Gate, follow-ups, rainfall, labels, health card. Pure functions, 142 tests. |
| W6 AI | Done. Model sweep on a fake client, benchmark, agreement, ablation, the checker. No paid call has ever run. |
| W7a Tools | Done. Audit log, photo ingest and blind labelling, preflight (17 checks), submit check, third party list. |
| W7b Docs | Done. Sourced lesson drafts, glossary, candidate sentences, region pack, human packs, video script, Devpost draft, README. |
| W8 Review | Done. docs/reviews/REVIEW_01.md: eight findings fixed, the rest deferred with one line each. |

## Proofs

- P1 walking skeleton: PASS. `docker compose up -d` then `uv run python scripts/smoke.py` prints landing 200 in about 90 ms, api health ok, a database row written and read back.
- P2 the record validates: PASS, and no fallback is in force. Our Bundle validates against their profiles built from hl7-eu/oah at b907cf0 with 0 errors. Fallback F2 (plain R4) is NOT needed. Evidence: results/fhir_validation.json, docs/fhir_mapping.md.
- K6 sandbox write: PASS on 2026-09-20 21:37Z. One tagged Location, create 201, read 200, delete 200, read after delete 410. Evidence: docs/notes/sandbox_write_test.txt, fhir/sandbox_ledger.jsonl. The mirror is built and stays behind SANDBOX_MIRROR_ENABLED.

## The next five steps

1. Rachel's photos land. `uv run python scripts/ingest_photos.py <folder> <labels.csv>` then `uv run python scripts/check_manifest.py`.
2. Both label blind. `uv run python scripts/label_photos.py --name rachel` and `--name alex`, then `uv run python scripts/merge_labels.py --apply`, which must print kappa per feature and no disagreements.
3. Freeze and register. `uv run python scripts/freeze_key.py`, then tag: `git tag prereg-v1 && git push origin prereg-v1`, then `uv run python scripts/preflight.py` must print 0 failed.
4. The real model run, on this Mac. The key goes in `.env` in this repo; it does not need a second machine. The only rule is that Alex never exports it in the shell that starts `claude`. Check the three model ids and prices first, flip the two confirmed flags, put the key in `.env`, then `uv run python evals/model_sweep.py --real`.
5. Deploy and launch. `fly auth login`, `vercel login`, `make deploy`, then post the link. After the lock on 2026-09-28T01:00:00Z, `uv run python evals/usability_analysis.py`, `make render-readme`, `make submit-check`.

## Traps

- `make check` needs Java 17: `export JAVA17_HOME=/opt/homebrew/opt/openjdk@17`.
- A stale compose volume breaks the migration. `docker compose down -v` before a rebuild.
- Never create the prereg-v1 tag until Rachel's wording is frozen; the analysis refuses without it and refuses a plan that differs from the tagged one.
- `--now` and `--repo` on the analysis are test only now and refuse outside a test.
- Fake model runs write results/cost_log_fake.jsonl. The real cost log stays about money.
- Tests point the audit log and the sandbox ledger at a temporary folder. Never run a test with AUDIT_LOG_PATH unset in a shell where it matters.
- The sandbox is shared: conditional creates only, delete only a ledger id, never by search, never expunge.
- Update 03 was never pasted into the terminal. P1, P2, P3, K6 and F2 were inferred from Update 04. If Update 03 exists, paste it and check docs/KILL_TESTS.md against it.
- One browser now keeps one arm. A test that wants many randomized visitors needs many client tokens.
