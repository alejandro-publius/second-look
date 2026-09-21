# Kill tests

Tests whose failure would sink the project. Each gets a result line with a date and a pointer to
the evidence. Only a person or the integrator marks a result; workstreams add rows as pending.

The original numbering K1 to K5 came from Update 03, which was never pasted into this terminal
(docs/DECISIONS.md, 2026-09-20). K6 came from Update 04 by name. The K1 to K5 rows below are
inferred from the master brief and Update 02 and 04: the five things the plan cannot survive
without. When Update 03 arrives, check its wording against these and fix the rows, not the code.

| Id | Test | Result | Evidence |
|---|---|---|---|
| K1 (inferred) | The HL7 validator accepts our record against their profiles at hl7-eu/oah b907cf0 (P2) | PASS 2026-09-20: 0 errors, 15 warnings, terminology checks off | results/fhir_validation.json, docs/fhir_mapping.md, docs/BUILD_LOG.md Phase 1 |
| K2 (inferred) | The compose stack serves web, API and Postgres and a row is written and read back (P1) | PASS 2026-09-20: landing 200 in 131 ms, api health ok, db rows 1 then 2 | docs/BUILD_LOG.md Phase 1, scripts/smoke.py |
| K3 (inferred) | Real photos and two blind labels arrive in time: 16 test photos with kappa written, key frozen, no ambiguous test photo | pending, Rachel by Tue Sep 22 noon, Alex's second labels the same day | results/key_agreement.json, results/key_hash.json, audit/log.jsonl (key_frozen) |
| K4 (inferred) | Enough strangers: at least 20 completed sessions per arm by data lock 2026-09-28T01:00:00Z, else the result is reported as a description only | pending, recruiting from Wed Sep 23 | GET /api/test/counts, results/usability_<stamp>.json |
| K5 (inferred) | A real vision model takes the same 16 item test through the batch API and the pass table says real true (P3) | pending, needs ANTHROPIC_API_KEY in .env and probe photos; fake client only until then | results/model_pass_table.json, results/cost_log.jsonl, audit/log.jsonl (model_pass_table) |
| K6 | The shared sandbox accepts one tagged Location by conditional create, returns it, and deletes it by id | PASS 2026-09-20 21:37Z: create 201 (id 451), read 200, delete 200, read after delete 410 | docs/notes/sandbox_write_test.txt, fhir/sandbox_ledger.jsonl |
| K7 | The gate holds: for any model output, stored answers equal the human answers and every label is a function of human answers alone (Hypothesis fuzz test) | pending W5; the test must be red when the gate is broken on purpose | core/tests/test_gate*.py |
| K8 | No client address reaches our server log during a full session, and no request leaves our origin (Playwright network log) | pending W1 and W4; run against the compose stack in Phase 3 | apps/api/tests, apps/web/tests, make e2e |
| K9 | `make preflight` fails only for human reasons on the placeholder build, and passes on the fully faked green fixture | PASS 2026-09-20: scripts/tests/test_preflight.py green; live run below | scripts/preflight.py, this session's report |
| K10 | The analysis refuses real data before lock and refuses to run without the prereg-v1 tag | pending W2; try it on purpose in Phase 4 | evals/usability_analysis.py, evals/tests |

How to log a result: replace "pending" with PASS or FAIL, the UTC date, and one line of what
was seen, then point at the file that proves it. Never edit a PASS into the row without the
evidence file existing.
