# PLAN.md: Second Look build plan

Version 2, Sun Sep 20 2026. Folds docs/internal/updates/UPDATE_02.md into the plan from docs/internal/MASTER_BRIEF.md section 17. Precedence: the latest file in docs/internal/updates/ wins over the brief; the brief wins over this plan unless a change is recorded in docs/DECISIONS.md.

Tags: MUST before the Wednesday Sep 23 launch. SHOULD before the Saturday Sep 26 freeze. COULD only if everything above it is green.

## How we work

Alex works only in this terminal and relays reports to the planner. Every session, and every decision point, ends with the report block from docs/internal/updates/UPDATE_02.md section 1 and nothing after it. Short replies, paths and key lines only, targeted tests while working, one full `make check` per milestone.

## Decisions made now, one path each

- Hosting: Cloudflare only (Update 09, docs/notes/hosting.md). Pages serves the static export of the web app; a TypeScript Worker on D1 serves the API, with KV for photo bytes. Workers do not sleep, so no ping job is needed. Cost through Oct 15: nothing, and no card. Time to first screen is measured and reported anyway.
- Backups: a daily D1 export kept as a private GitHub artifact (`.github/workflows/backup.yml`), manual only until the two secrets exist. A restore drill runs once before launch. Amendment 5 is satisfied without a new service.
- Uploads (rung 2) live in Workers KV with a 30 day expiry, not a cloud bucket. No new account, same privacy.
- Python 3.12 through uv. Local Node 26, CI Node 20. Next.js App Router. Playwright with axe-core.
- FHIR toolchain pins in CI: SUSHI 3.20.1, Node 20, Java 17, one validator jar version recorded in fhir/ig.lock, `~/.fhir/packages` cached. If the terminology server is unreachable, the validator reruns with terminology checks off and the results file says so. Locally the validator runs in Docker because this Mac has Java 8.
- IG pin: hl7-eu/oah commit b907cf0 is the current HEAD (2026-06-11). Confirmed Sep 20. The package is built from source; the .tgz is never committed because their repo has no LICENSE.
- Model ids claude-haiku-4-5-20251001, claude-sonnet-5, claude-opus-5 match the current list. Re-checked before the first paid run.
- Codes: their TemporaryOahSystem `present` and `absent` for feature answers and their codes `morophology`, `invasiveOrganisms`, `LandUse`, `foam`, `riparianVegetation` where an item maps; our CodeSystem only for artificial_bank, pipe_running and cant_tell. Values are CodeableConcepts, never booleans, because their Observation profile allows only CodeableConcept or Quantity.
- The no-third-party-origin rule covers the study flow, consent through end screen. The rung 2 map pin uses a tile server declared in docs/DATA_HANDLING.md.
- One UTC constant for data lock: 2026-09-28T01:00:00Z. Stored times are UTC, shown in local time.
- The launch wipe is a command, `scripts/wipe_for_launch.py`, which writes its own line to docs/deviations.md and to the audit log.
- `scripts/sandbox_write_test.sh` did not exist on disk, so it was written today: one tagged Basic resource, conditional create, read back, ledger entry, delete by that id only.
- The analysis plan is not written yet, so the section 2 amendments go into it at first writing in Session A; no edit of a tagged plan is needed.

## Sessions

Each session ends with a proving command and the report block. Output of the proving command is pasted into docs/notes/session_<letter>.md.

### Session A, Sun Sep 20, tonight, about 5 hours. MUST.

Goal: backend and analysis for the usability test, placeholders easy to swap.

Order:
1. Scaffold: uv project; `apps/api`, `core`, `content`, `evals`, `results`, `scripts`, `fhir`, `audit`, `docs`; Makefile with `dev`, `check`, `preflight`, `submit-check`; GitHub Actions running `make check`; `.env.example`; README stub with the section 12 headings and the take-the-test line; docs/THIRD_PARTY.md, docs/DECISIONS.md, docs/deviations.md, docs/track_statement.md (word for word from UPDATE_02 section 11.12).
2. Content: features, lessons, california-bay-area region, approved_sentences (schema, empty list), locales/en.json, glossary. App-mirroring items pre-filled from the app's public text with `verified_against_app: false`. `photos/manifest.csv` with 40 labelled gray placeholders. `core/content_loader.py` with every fail-loud check from brief section 6.
3. API: tables `session` (plus `source` label and `honeypot_filled`) and `response`; allocator for k arms, permuted blocks of 4, stored seed; the six endpoints; export with no identifier columns; counts endpoint with counts by arm and by source only; `/demo` never stores; in-memory rate limit that never touches disk or logs.
4. Analysis: `core/lock.py` with the UTC constant and the one-second-either-side test; `evals/make_synthetic_sessions.py` (no effect, real gain, yes bias); `evals/usability_analysis.py` (bootstrap, permutation test, Hedges g, sensitivity checks, refuses real data before lock, refuses to run without the tag or with a changed plan); `evals/power.py`.
5. Gate: `core/gate.py` with the Flag model and the hypothesis fuzz test; record builder that accepts human answers only.
6. Sweep: `evals/model_sweep.py` against a fake client; `results/model_pass_table.json` labelled `real: false`.
7. Claims and plan: `scripts/verify_claims.py`; `docs/analysis_plan.md` word for word from brief section 7 with the eight amendments from UPDATE_02 section 2 folded in.

Tests that must pass: arm balance within blocks; lesson and test photos disjoint by hash and scene_id; test set is 16 with 2 present and 2 absent per feature; idempotent responses; export has no identifier columns; counts endpoint returns counts only; a response one second after lock is excluded and one second before is kept; analysis recovers a planted effect, rejects about 5 percent under no effect, shows no gain under yes bias; analysis refuses real data without the tag; gate fuzz; verify_claims passes on the stub.

Proving command: `make check` green locally and in CI, then `uv run python evals/usability_analysis.py --synthetic all` prints the three results tables.

Not tonight: UI beyond a health page, FHIR, uploads, the checker, any call to OneAquaHealth systems.

### Session A2, short, right after A. MUST.

- `evals/consensus.py` implementing amendment 6 exactly; writes `results/consensus_<date>.json` and one chart. Two synthetic cases: mixed skill where the scored vote must beat the plain vote, and equal skill where the two tie within noise.
- `scripts/ingest_photos.py`: folder of HEIC or JPEG originals plus a labels CSV in; EXIF-stripped, resized images and manifest rows out; hashed after processing; originals never enter the repo.
- `scripts/label_photos.py`: a local page that writes `labels_<name>.csv` and never shows the other labeller's file. `scripts/merge_labels.py`: Cohen's kappa per feature, every disagreement listed, refuses to freeze the key while any remain.
- `audit/log.jsonl` hash chain (seq, ts_utc, kind, payload_sha256, prev_hash, hash) and `scripts/verify_audit.py`. About 50 lines, no new dependency.
- `docs/release_form.md` (plain one-page template, not legal advice) and a first `docs/DATA_HANDLING.md`.

Proving command: `uv run pytest -q evals/tests/test_consensus.py scripts/tests` green; `uv run python scripts/verify_audit.py` prints the chain length and last hash.

### Session B, Mon Sep 21, about 4 hours. MUST except the poster's A4 size.

Goal: the brief section 6 flow as a Next.js PWA, deployed, with the poster and the share card.

Build: static landing that paints at once and wakes the API in the background; consent with version stamp and the hidden bot-trap field; warm-up; assignment call; lesson cards with progress and per-screen seconds; 16-item test with Yes, No, Can't tell and glossary tooltips; end screen with per-feature score, the prior-experience question and a share card whose preview image is rendered on the server from the score alone; `?src=` carried into the coarse source label; `/demo` with per-answer feedback, a summary of missed features and only those lessons, never stored; `/health`. Poster: HTML to PDF with Playwright, Letter and A4, two warm-up photos, the question, "Scan to find out. Two minutes. Anonymous.", QR to `?src=poster`, no answer printed.

Deploy: the Worker on D1 for the API; the Pages project for the web; environment variables; `make preflight --remote` smoke mode.

Proving command: `npx playwright test` green for both arms on a phone viewport including the third-party request check; the public URL completes one QA session flagged `is_test` from Alex's phone; the report states the measured cold-start time to first screen.

### Session C, Tue Sep 22, about 4 hours. MUST. Needs Rachel's photos and labels by 19:00.

Goal: real content in, plan frozen, tag, real model run.

Do: `scripts/ingest_photos.py` on Rachel's folder; both labellers label through `scripts/label_photos.py`; `scripts/merge_labels.py`, settle every disagreement, remove any photo either called ambiguous; `scripts/freeze_key.py` (audit kind key_frozen); freeze the four question wordings in docs/analysis_plan.md; dry run with three friends; fix confusions; `scripts/wipe_for_launch.py` (audit kind launch_wipe); restore drill from a volume snapshot; `make preflight`, which now also verifies the audit log, the hidden field and the UTC lock; commit; tag `prereg-v1` (audit kind plan_tagged); print the plan's SHA-256 for Alex to post; run `evals/model_sweep.py` for real through the batch API; commit results and cost log, failures included (audit kind model_pass_table).

Proving command: `make preflight` prints every check passed; `git show prereg-v1 --stat`; `uv run python scripts/verify_claims.py` passes; `results/model_pass_table.json` has `real: true`; `uv run python scripts/verify_audit.py` passes.

### Launch, Wed Sep 23 morning

Alex posts the link and the poster. Until lock the only study numbers anyone sees are `GET /api/test/counts`: completed sessions by arm and by source.

### Session D, Wed Sep 23 and Thu Sep 24, about 3 hours each. Core is MUST for rung 2; additions are SHOULD.

Build: `content/form.yaml` in the app's order from Alex's screenshots; `content/followups.yaml`; `core/followups.py` as a pure function with the two-question cap; Open-Meteo rainfall client with caching, attribution and the 72 hour, 2.5 mm rule in config; guided check UI, one question per screen, one-handed; analyst view with each answer beside the observer's per-feature score, the checks that ran, and the toggle "show only answers from people who passed this feature".

SHOULD: fail-closed rules, so a failed rainfall or location lookup skips the dry pipe question, and a denied location permission offers a dropped pin or a saved spot. Uploads: images only, real type checked, size capped, downsized on the phone, stored on the private volume, deleted after 30 days.

COULD (moved down from SHOULD, see Skipped): the offline queue with "saved on this phone, will send later".

Proving command: pytest passes one test per follow-up rule plus the cap and the fail-closed cases; a Playwright run files one creek check end to end on a phone viewport and opens the analyst view.

### Session E, Fri Sep 25, about 5 hours. Record and mirror MUST for rung 2; viewer and proposal SHOULD.

Build: docs/fhir_mapping.md first; `fhir/ig.lock`; FSH for our CodeSystem, both Questionnaires, the Practitioner qualification and our Organization; `core/fhir_emit.py`; SUSHI and the validator in CI with the pins above; our store of validated JSON; sandbox mirror with conditional creates, `meta.tag`, `fhir/sandbox_ledger.jsonl`, `scripts/repush_sandbox.py` (audit kinds record_written and sandbox_push); Postman collection; the Library entry; the health card from approved sentences only; quick check and timeline. If Alex's write test returned 401 or 403: no mirror, and a public read-only endpoint serves our validated records instead.

SHOULD: the two-observer viewer. Read-only GETs to the sandbox at one per second, 50 per session, user agent naming the repo; a few published Almyros water chemistry Observations cached in our database, never in git; the same record component renders theirs and ours; if the sandbox is down the screen says so and shows ours alone. "View as FHIR" on every record: JSON, a badge with the guide commit it validated against, a copyable curl line. `docs/ig_proposal.md` with an FSH example that builds inside a copy of their guide at the pinned commit.

Proving command: `make check` runs FHIR validation with zero errors; `uv run python scripts/repush_sandbox.py --dry-run` lists what would be written; one real push; a GET of our Provenance by tag from the sandbox returns it.

### Session F, Sat Sep 26, about 5 hours. Checker and benchmark SHOULD; freeze MUST.

Build: vision checker limited to passed features and one follow-up slot; `evals/benchmark.py` with Wilson intervals; `evals/agreement.py` on a 50 photo overlap; `evals/ablation.py`; adversarial photo test; rotate new photos into the test pool; `evals/pick_examples.py` choosing the three test items with the largest trained-arm versus best-model gap; `/demo?script=1` seeded path; docs/video_script.md from UPDATE_02 section 13 tied to real screens; accessibility pass; freeze at night with the audit log's last hash printed in the README for Alex to post.

Proving command: `make check` green; `results/benchmark.json`, `results/ablation.json`, `results/examples.json` committed; the adversarial test passes; `scripts/verify_audit.py` prints the freeze hash.

### Session G, Sun Sep 27 after the 18:00 PDT lock (01:00 UTC Mon), about 4 hours. MUST.

Do: audit kind data_lock; export the response table; run `evals/usability_analysis.py` once on real data; run `evals/consensus.py` on real data and place its chart; generate the README table from `results/`; `verify_claims`; README in the brief's section 12 shape with the track statement as its first line and the take-the-test line at the top; docs/devpost.md mapping every field from docs/notes/devpost_fields.md to a README section; docs/SUBMISSION_CHECKLIST.md and `make submit-check`; architecture diagram in their five pipeline stages; the One Digital Health and FAIR box; known weaknesses.

Proving command: `uv run python scripts/verify_claims.py` passes with zero hand-edited numbers; `make submit-check` passes every item except "repo is public", which flips on Sep 30; `git diff --stat prereg-v1 -- docs/analysis_plan.md` is empty or every change appears in docs/deviations.md.

### Mon Sep 28 to Wed Sep 30

Mon: record and edit the video to about 3:45; full dry-run submission by midnight. Tue: fixes only, after 19:00. Wed: repo public, `make submit-check` fully green, incognito check, submit by 18:00 PDT.

### COULD, in this order, only if everything above is green

1. Spanish locale, only with a named fluent checker recorded in the locale file.
2. Small read-only MCP server over our own records: get a creek's record, list visits, get an observer's score.
3. The note on reaches downstream of a finding.
4. The pull request to hl7-eu/oah with the citizen example; Alex opens it himself once the repo is public.
5. The offline queue for the guided check.

## Skipped or downgraded, with reasons

- Offline queue (UPDATE_02 section 10): downgraded from SHOULD to COULD. A service worker plus an IndexedDB queue for answers and photo blobs plus sync conflict handling is at least an evening on its own, and Session D already holds the form, follow-ups, rainfall and analyst view. The fail-closed rules from the same section stay SHOULD because they are cheap.
- Scheduled ping every 10 minutes (section 11.3): not needed, a Worker does not sleep.
- Cloud bucket for uploads (section 11.8): replaced by Workers KV with a 30 day expiry. Same guarantee, one fewer account.
- Spanish locale (section 9): stays COULD and ships only with a named checker.

## Inputs and latest workable dates

| Input | Who | Wanted by | Latest without moving launch or lock |
|---|---|---|---|
| Run `bash scripts/sandbox_write_test.sh` and save the output to docs/notes/sandbox_write_test.txt | Alex | today | Thu Sep 24 |
| Strawberry Creek trip: shot list photos, video footage, one official app assessment with a screenshot of every screen | Alex | today | Tue Sep 22 19:00 |
| Hackathon Slack: channel list, pinned posts, any data set or recording links, to docs/notes/slack.md | Alex | today | Wed Sep 23 |
| Devpost Create Project form fields to docs/notes/devpost_fields.md, and whether a one-person team is refused | Alex | today | Sun Sep 27 |
| Five lines on their AI image model video to docs/notes/their_image_model.md | Alex | today | Sun Sep 27 |
| API workspace spend limit and alert set | Alex | today | Tue Sep 22 19:00 |
| Consent contact email | Alex | Mon Sep 21 | Mon Sep 21 18:00 |
| Cloudflare account, logged in through wrangler, no card needed | Alex | done Sep 20 | done |
| ANTHROPIC_API_KEY with a few dollars of credit, in .env only | Alex | Tue Sep 22 | Tue Sep 22 19:00 |
| About 40 photos per the shot list, originals kept, spot and date noted | Rachel | Tue Sep 22 12:00 | Tue Sep 22 19:00 |
| Gold labels for the 16 test photos, blind, through scripts/label_photos.py | Rachel | with the photos | Tue Sep 22 21:00 |
| One rule of thumb per feature with a source, and the four question wordings | Rachel | Tue Sep 22 12:00 | Tue Sep 22 21:00, frozen at the tag |
| Bay Area invasive list checked against the Cal-IPC inventory | Rachel | Tue Sep 22 12:00 | Tue Sep 22 19:00 |
| Independent second labels through scripts/label_photos.py | Alex | Tue Sep 22 evening | Tue Sep 22 22:00 |
| Approved health and ecology sentences after the indicator factsheets | Rachel | Fri Sep 25 | Sat Sep 26 12:00 |
| One creek visitor on camera taking the test, with a signed release | Both | Sun Sep 27 | Mon Sep 28 15:00 |
| Permission from ENORA for their site list or the Resilience Map API | Alex | optional | never required |

## Cut order if a session runs late

1. Everything tagged COULD.
2. Rung 3 ablation and the 150 photo benchmark. Keep the 16 item model comparison.
3. The two-observer viewer and the proposal page.
4. Rung 2 quick check and timeline.
5. Rung 2 sandbox mirror. Keep local validated records and the Postman collection.
6. Never cut: consent, the gate, preflight, the tag, verify_claims, the audit log, the README first screen, `make submit-check`.

## Risks

- Photos arrive late: the launch slips one day per day late. The lock does not move, so the sample shrinks.
- Nobody is recruited (Update 14 section 0). Any sessions that arrive are reported as a description with their count. Fallback F1 is the standing plan, not a fallback.
- Another team wipes the sandbox: repush from our store; the ledger makes it a one-command fix; the sandbox part of the video is recorded the day it first works.
- Every vision model fails every feature: the checker ships with zero flags and the README says where AI should stay quiet.
- The Devpost form refuses a one-person team: add Rachel as a teammate before Sep 28.

## Decision points

From docs/internal/updates/UPDATE_03.md, recovered on 2026-09-21. The current state of each kill test is
in docs/internal/KILL_TESTS.md.

- **Launch decision, Tuesday Sep 22 at 22:00 PDT.** Go if P1 passed, K3 and K4 passed for at
  least three features, and `make preflight` is green. Otherwise do not launch a test we cannot
  stand behind. Take F1 and keep building the record. **P1 has not passed as written**: the
  skeleton runs on docker compose, not on a real host, because no hosting account existed
  yet. That is the single thing most likely to stop the launch. (Since Update 09 it runs on
  Cloudflare and P1 passed there; see docs/internal/KILL_TESTS.md.)
- **Reach check: decided on Sep 21, not on Sep 24.** Nobody is recruited, so the headline is F1
  from here: the full loop, the AI on the same 16 photos and on open creek footage, and a citizen
  record validated in their own format. Whatever sessions arrive are reported as a description
  with their count. The analysis plan is unchanged; only the emphasis is (Update 14 section 0).
- **Spend checks.** API spend above 150 dollars by Sep 23 or 350 dollars by Sep 26 means routine
  sessions drop to the cheaper model and nothing tagged COULD is built. If Alex reports his weekly
  usage limit above 90 percent before it resets, stop COULD and SHOULD work and ask him whether to
  move this terminal to API billing on the capped workspace.
- **Freeze, Saturday Sep 26 at night.** Whatever is not green is cut from the story, not patched
  on Sunday.

## Fallbacks

- **F1. The lesson shows no clear effect, or too few people came.** The headline becomes: the
  score travels with every observation, AI took the same test, and a citizen record sits validated
  in their own format. The test is reported exactly as it came out, small and honest. Track 3
  still holds if the model run shipped. Nothing already built is wasted.
- **F2. Their profiles reject a citizen record, or the sandbox refuses writes.** The headline
  becomes the lesson and the test on strangers, entered in Track 1. The FHIR work ships as plain
  valid R4 plus docs/ig_gap_report.md. **Not in force:** P2 passed with terminology on and K6
  passed, both recorded in docs/internal/KILL_TESTS.md.
- **F3. A feature cannot be photographed or labelled reliably.** Three features, 12 items, written
  into the plan before the tag.
- **F4. The models ace the early photos.** The checker is described as a second pair of eyes that
  earned its place on the same test. The person still goes to the creek, because a model cannot
  smell the water, see the pipe behind the bush, or know that it has not rained. If the models
  fail everything, the README says where AI should stay quiet, which is also an answer the track
  asked for.
- **F5. The hook pair is too easy.** One photo and "what is wrong with this creek?".

## Proposed changes to the brief, awaiting the planner

Each with the reason in a line. Items 1, 2, 4, 5, 6 and 9 are already reflected in the decisions above because Session A cannot be built without choosing; the planner can reverse any of them.

1. Use their codes where they exist, ours only where they do not. Their value set already has `present` and `absent`, and codes for channel morphology, invasive organisms, land use, foam and riparian vegetation. The "same value sets as lab data" sentence then holds word for word.
2. Feature answers as CodeableConcepts, not booleans. Their Observation profile rejects any other value type.
3. Pre-fill the app-mirroring items from the app's public frontend text saved at ~/scratch/oah-research/, marked unverified until Alex's screenshots. Exact wording in seven languages, from a static page and not from api.enora-oah.eu, and it saves Alex an evening of typing.
4. Production database: Cloudflare D1, which is SQLite, instead of Postgres. Eighty sessions do not need a second service, and data lock becomes one export.
5. Scope the no-third-party-origin rule to the study flow. A map pin in rung 2 cannot exist without a tile server.
6. Add to rule 10: the sandbox has no StructureDefinitions loaded, so it validates nothing, and on Sep 20 it held zero Provenance and zero QuestionnaireResponse resources. Our CI is the only validator, and the README can say, with the date, that ours are the first citizen records there.
7. Drop the wait for a "Session 5 recording". Only five sessions exist, the fifth ran Sep 16 with no recording posted, and there is no Session 6.
8. Claim wording: another entry, stream-to-clinic, already validates against the OneAquaHealth profiles in CI. We claim the first citizen record whose contributor score travels in Provenance, not the first to validate.
9. `scripts/wipe_for_launch.py` writes its own deviations entry. A hand-written log line is the kind of number rule 12 forbids.
10. Video script correction: the app records foam and colour but has no smell item. Our own quick check may ask about smell; the app does not.
