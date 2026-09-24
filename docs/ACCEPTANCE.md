# Acceptance: every gate, and the command that proves it

One row per promise this project makes. The command is the proof. If a command does not print
what the row says, the promise is not kept, whatever any page claims.

Run everything from the repository root. `make judge-check` runs the first five rows on its own,
offline, with no API key, and prints a five line summary.

## Setup, once

```
uv sync
cd apps/web && npm install && cd ../..
export JAVA17_HOME=/opt/homebrew/opt/openjdk@17   # the FHIR validator needs Java 17
```

Nothing below needs an API key. Nothing below needs a network except the two rows that say so.

## The gates

| # | The promise | Command | What it prints when it holds |
|---|---|---|---|
| 1 | Everything is tested | `make test` | the pytest line with 0 failures |
| 2 | The edge is the same function twice, not a second opinion | `make worker-check` | `build-worker-content` and `golden-vectors` both up to date, then the Worker's own suites pass |
| 3 | Every record their systems could not read is stopped here | `make fhir-validate` | validated against `hl7-eu/oah` at `b907cf0` with 0 errors |
| 4 | No number in the README was typed by hand | `make verify-claims` | every claim matched against `results/` |
| 5 | The audit log has no break in it | `make audit-verify` | the entry count, `chain intact`, and the last hash |
| 6 | Every image a person sees has a manifest row | `make manifest-check` | the image count, all with matching rows |
| 7 | Plain words, reading age about 12 | `make readability` | the string count, the average grade under the cap, the exception count |
| 8 | No em dash, no en dash, anywhere | `make dash-check` | no long dashes in tracked files |
| 9 | Every diagram in the docs renders, and the SVGs in `docs/diagrams` are what their sources draw | `make diagrams` | the block count, parsed; the source count, every edge labelled; each SVG the same as a fresh render |
| 10 | Colour, spacing and tap targets come from tokens | `make design-check` | clean, with the contrast pairs computed and the tap targets measured |
| 11 | The app builds as a static export | `make web-build` | `web build ok` |
| 12 | Everything above, in one run | `make check` | `CHECK GREEN` |
| 13 | The launch gate | `make preflight-launch` | `0 failed` |
| 14 | The submission gate | `make submit-check` | every item except the video link and the repo being public |
| 15 | One command for a judge | `make judge-check` | five lines, all PASS: the Python tests and the Worker's golden vector tests; the last HL7 validator run read from `results/fhir_validation.json` (it does not run the validator; row 3 does) and the golden Bundles checked against the emitter; the web build and the design check; the audit log; the secrets scan |

## The gates that need a network or a browser

| # | The promise | Command | What it prints when it holds |
|---|---|---|---|
| 16 | A person can finish the test on a phone | `cd apps/web && npx playwright test` | every spec passing on the 390 by 844 viewport, both arms |
| 17 | The whole API works on the edge runtime | `make worker-e2e` | 9 sections green under `wrangler dev` |
| 18 | The deployed site is the one we think it is | `DEPLOYED_URL=... DEPLOYED_API=... npx playwright test tests/deployed-smoke.spec.ts` | a whole sitting finished, and the counts endpoint did not move |
| 19 | The landing page paints fast enough on a slow phone | `SITE_URL=... node apps/web/scripts/live-check.mjs` | load and largest paint under the 3 second line on a throttled 4G profile |

## The rules that are enforced by a test, not by a command

These are the ones worth arguing about, so each names the test that would go red.

| Rule | Where it is enforced | The test that catches a breach |
|---|---|---|
| A model's output becomes a `Flag` or is rejected. There is no third path. | `core/gate.py` | `core/tests/test_gate.py`, including a hypothesis fuzz over arbitrary model output |
| A model may flag a feature only if it passed the same test the volunteers took | `core/gate.py`, `core/checker.py` | `core/tests/test_checker.py::test_unpassed_feature_returns_nothing_even_when_the_model_is_confident` |
| A synthetic pass table can never license a flag in production | `core/checker.py` | `core/tests/test_checker.py::test_synthetic_pass_table_never_licenses_a_flag_by_default` |
| At most two follow-up questions, at most one of them from a model | `core/followups.py` | `core/tests/test_followups.py`, one test per rule plus the cap |
| No model call inside follow-up selection | `core/followups.py` | the module imports nothing that can reach the network; `core/tests/test_followups.py` is pure |
| Every health or ecology sentence comes from an approved sentence with a source | `content/approved_sentences.yaml`, `core/labels.py` | `core/tests/test_labels.py`; an unapproved sentence is absent and the page says why |
| The analysis refuses real data before the lock | `core/lock.py`, `evals/usability_analysis.py` | `core/tests/test_lock.py`, one second either side of `2026-09-28T01:00:00Z` |
| The analysis refuses a plan that differs from the tagged one | `evals/usability_analysis.py` | `evals/tests/test_usability_analysis.py` |
| No identifier column ever leaves in an export | `apps/api/study.py` | `apps/api/tests/test_privacy.py` |
| The counts endpoint returns counts only | `apps/api/study.py`, `worker/src/index.ts` | `apps/api/tests/test_study.py` and `worker/test/e2e.mjs` |
| A test photo and a lesson photo are never the same scene | `scripts/check_manifest.py`, `core/content_loader.py` | `make manifest-check`, and the disjoint check inside `core/content_loader.py` that `make check` runs |
| Uploads lose their metadata and expire after 30 days | `worker/src/uploads.ts`, `apps/api/check.py` | `apps/api/tests/test_upload.py::test_upload_strips_exif_downsizes_and_serves_only_with_the_token`, and the uploads section of `worker/test/e2e.mjs` |
| A coarse pin is never compared against another pin | `core/act.py` | `core/tests/test_act.py::test_a_spot_with_no_position_is_skipped` and `::test_a_finding_on_an_unknown_reach_gives_no_note` |
| The sandbox is only ever written with conditional creates, and deleted only by ledger id | `scripts/repush_sandbox.py` | `scripts/tests/test_repush_sandbox.py` |
| A frame's label comes from the video's own description or the frame is unlabelled | `videos/manifest.csv`, `scripts/make_frames.py` | `scripts/tests/test_make_frames.py`; the method is in `docs/REAL_VS_SYNTHETIC.md` |

## Beyond the gates

| The promise | Command | What it prints when it holds |
|---|---|---|
| Everything a contributor runs | `make check` | `CHECK GREEN` |
| The Worker behaves end to end with a local D1 | `make worker-e2e` | exit code 0 |
| The launch gate for the two-minute test | `make preflight-launch` | 0 failed |
| The submission gate | `make submit-check` | fails only on `video_link` and `repo_public` until Sep 30, then nothing |
| No video file is ever committed | `uv run pytest -q scripts/tests/test_no_video_files.py` | 2 passed |
| The live site answers, and a phone check writes nothing | `SITE_URL=https://second-look-79t.pages.dev node apps/web/scripts/live-readonly.mjs` | every step PASS, the counts unchanged |

## What a failure here means

A red row is not a bug to be worked around. Every row above exists because a specific thing could
go wrong quietly: a model deciding something, a number drifting away from its source, a record
their systems cannot read, a person's details reaching a page. If a row goes red the honest move
is to stop and say so, which is what `docs/deviations.md` is for.
