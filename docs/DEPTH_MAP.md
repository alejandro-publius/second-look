# Depth map

One row per feature, built by reading the repo at commit f85e3cf, not from memory. Status is
**built** (works and has a test), **parked** (exists but is switched off, placeholder or partial)
or **missing** (not written).

Rubric weights: Impact and alignment 30, Innovation 20, Technical 20, UX 15, Feasibility and
scale 15.

## TRAIN

| Feature | Status | Main file | Test | Rubric line | Judge who cares |
|---|---|---|---|---|---|
| Two minute photo test, 16 items, select then Next | built | `apps/web/components/TestItems.tsx` | `apps/web/tests/test-flow.spec.ts` | UX, Innovation | outreach, ecologist |
| Permuted block randomization, replayable from a seed | built | `core/allocator.py` | `core/tests/test_allocator.py` | Technical | data tools |
| Per feature score, 4 items each | built | `core/scoring.py` | `core/tests/test_scoring.py` | Innovation | data tools |
| Lesson: rule of thumb, contrast pairs, practice | parked (copy is PLACEHOLDER) | `apps/web/components/Lesson.tsx` | `apps/web/tests/test-flow.spec.ts` | UX | ecologist, outreach |
| Marks on lesson photos, placed and approved by a person | built (marks are placeholders) | `scripts/label_photos.py` | `scripts/tests/test_mark_photos.py` | UX | ecologist |
| Resume a sitting after a reload | built | `apps/api/study.py`, `worker/src/index.ts` | `apps/web/tests/resume.spec.ts` | Technical | data tools |
| Judge mode, shut until data lock | built | `apps/web/app/demo/page.tsx` | `apps/web/tests/demo.spec.ts` | Technical | data tools |
| AI takes the same 16 item test | parked (fake client only, no paid run) | `evals/model_sweep.py` | `evals/tests/test_model_sweep.py` | Innovation | digital health |
| Model pass table gates flags | built | `core/checker.py` | `core/tests/test_checker.py` | Innovation | digital health |
| Photos: open search, contact sheets, picking, ingest | built | `scripts/find_open_photos.py` | `scripts/tests/test_find_open_photos.py` | Feasibility | outreach |
| Real photographs in the test | missing (all 40 are placeholders) | `photos/manifest.csv` | `scripts/check_manifest.py` | Impact | ecologist |

## CHECK

| Feature | Status | Main file | Test | Rubric line | Judge who cares |
|---|---|---|---|---|---|
| Guided creek check in the app's own questions | built | `apps/web/components/CheckFlow.tsx` | `apps/web/tests/check.spec.ts` | Impact, UX | ecologist |
| Question wording taken from the app's public text | built for 2 of 4 | `docs/notes/app_strings.md` | `scripts/preflight.py` | Impact | ecologist, standards |
| 20 second return check | built | `apps/web/components/QuickCheck.tsx` | `apps/web/tests/record.spec.ts` | UX | outreach |
| Offline queue at the creek | built | `apps/web/lib/offline.ts` | `apps/web/tests/check.spec.ts` | Feasibility | outreach |
| Photo upload, EXIF stripped, private, 30 day delete | built (Python only) | `apps/api/routes_check.py` | `apps/api/tests/test_upload.py` | Technical | digital health |
| Coarse location unless the person places the pin | built | `apps/web/components/LocationStep.tsx` | `apps/web/tests/check.spec.ts` | Technical | digital health |

## VERIFY

| Feature | Status | Main file | Test | Rubric line | Judge who cares |
|---|---|---|---|---|---|
| Follow up selector, pure, at most two questions | built | `core/followups.py` | `core/tests/test_followups.py` | Innovation | data tools |
| The gate: model output becomes a Flag or is rejected | built | `core/gate.py` | `core/tests/test_gate.py` | Innovation, Technical | digital health |
| Rainfall lookup for the dry pipe rule | built | `core/rainfall.py` | `core/tests/test_rainfall.py` | Innovation | ecologist |
| A model may only ask where it passed | built | `core/checker.py` | `core/tests/test_checker.py` | Innovation | digital health |
| Duplicate pin guard, 30 metres | built | `core/act.py`, `apps/api/check.py` | `core/tests/test_act.py`, `apps/api/tests/test_city.py` | Technical | data tools |
| Test pin guard, names that look like tests | built | `core/act.py`, `apps/api/city.py` | `core/tests/test_act.py`, `apps/api/tests/test_city.py` | Technical | data tools |

## RECORD

| Feature | Status | Main file | Test | Rubric line | Judge who cares |
|---|---|---|---|---|---|
| FHIR emitter on their Location and Observation profiles | built | `core/fhir_emit.py` | `core/tests/test_fhir_emit.py` | Technical | standards |
| HL7 validator, their guide at b907cf0, terminology on | built, 0 errors | `scripts/fhir_validate.py` | `docs/notes/p2_validator_run.md` | Technical | standards |
| Observer score travels with every observation | built | `core/fhir_emit.py` | `core/tests/test_fhir_emit.py` | Innovation | standards, digital health |
| Provenance links an Observation to both responses | built | `core/fhir_emit.py` | `core/tests/test_fhir_emit.py` | Technical | standards |
| Our own read only FHIR endpoint | built (Python only) | `apps/api/fhir_routes.py` | `apps/api/tests/test_fhir_routes.py` | Technical | agents |
| Sandbox mirror, conditional creates, ledger | built, one write proven | `scripts/repush_sandbox.py` | `apps/api/tests/test_fhir_store.py` | Technical | standards |
| Library entry in their sandbox, the FAIR pattern | **missing** | none | none | Impact | standards |
| Hash chained audit log | built | `scripts/audit_log.py` | `scripts/verify_audit.py` | Technical | data tools |

## ACT

| Feature | Status | Main file | Test | Rubric line | Judge who cares |
|---|---|---|---|---|---|
| Health card for the person and the pet | built | `core/healthcard.py` | `core/tests/test_healthcard.py` | Impact | digital health |
| The record: a spot's timeline with scores beside answers | built | `apps/web/components/SpotRecord.tsx` | `apps/web/tests/record.spec.ts` | Impact | ecologist |
| Two observer screen, ours beside a laboratory result | built | `apps/web/components/TwoObservers.tsx` | `apps/web/tests/record.spec.ts` | Impact | standards |
| `/city`: what this creek needs, pipes worth testing | built | `core/act.py`, `apps/api/city.py` | `core/tests/test_act.py`, `apps/api/tests/test_city.py` | **Impact (30)** | ecologist, digital health |
| Measures from the decision tool, approved sentences only | built, empty until a sentence is approved | `core/act.py` | `core/tests/test_act.py` | Impact | ecologist |
| ServiceRequest referral for a pipe worth testing | built | `core/fhir_referral.py` | `core/tests/test_fhir_referral.py`, `apps/api/tests/test_city.py` | Impact | standards, digital health |
| A laboratory result returning to the same record | built, as a tagged example | `core/fhir_referral.py` | `core/tests/test_fhir_referral.py` | Impact | digital health |
| Downstream note on reaches below a finding | parked (pure function, nothing calls it) | `core/act.py` | `core/tests/test_act.py` | Innovation | ecologist |
| MCP server over our records, read only, local | **missing** | none | none | Innovation | agents |
| `make new-city`, the follower city recipe | **missing** | none | none | **Feasibility (15)** | outreach |

## The build, the docs and the gates

| Feature | Status | Main file | Test | Rubric line | Judge who cares |
|---|---|---|---|---|---|
| Live site and API on Cloudflare, no card | built | `worker/src/index.ts` | `docs/notes/hosting.md` | Feasibility | data tools |
| API on a second origin, so CORS is needed | parked (Update 10 A1 moves it) | `worker/wrangler.jsonc` | none | Technical | data tools |
| Launch gate and judges gate, split | built | `scripts/preflight.py` | `scripts/tests/test_preflight.py` | Feasibility | data tools |
| Daily backup, manual runs only until the secrets exist | parked (Update 10 A2) | `.github/workflows/backup.yml` | `scripts/tests/test_preflight.py` | Feasibility | data tools |
| Pre registered analysis plan, refuses before lock | built, not tagged | `evals/usability_analysis.py` | `evals/tests/` | Technical | data tools |
| Design tokens, one accent, the staff gauge | built | `apps/web/styles/tokens.css` | `apps/web/scripts/design-check.mjs` | UX | outreach |
| Photo credits, build fails without an author | built | `apps/web/app/credits/page.tsx` | `apps/web/tests/landing.spec.ts` | Technical | standards |
| `make judge-check`, one command for a judge | **missing** | none | none | **Feasibility** | all |
| Architecture diagrams that are checked to parse | **missing** | none | none | Technical | data tools |
| `docs/JUDGE_SCORECARD.md`, `docs/ACCEPTANCE.md` | **missing** | none | none | Feasibility | all |
| Spanish strings | **missing** | none | none | Outreach | outreach |
| Reading grade check on every UI string | **missing** | none | none | UX | outreach |

## Counts

| Status | Count |
|---|---|
| built | 39 |
| parked | 5 |
| missing | 9 |

Counted again on 2026-09-21 after Update 10 tier 1 items 1 to 3. The remaining missing rows are
the agents and integration line (the MCP server, the Library entry, `make new-city`) and the
documentation and gates of tier 3 and tier 4. What a city does with the record now exists; what an
agent can fetch does not yet.
