# PLAN.md: Second Look build plan

Written Sun Sep 20 2026 from docs/MASTER_BRIEF.md section 17. Status: waiting for Alex's approval before Session A starts. Where this file and the brief disagree, the brief wins unless a change below is approved and recorded in docs/DECISIONS.md.

## Decisions made now, one path each

- Hosting: web on Vercel (Hobby plan), API on one Fly.io shared-cpu machine with a 1 GB volume, SQLite on that volume. `DATABASE_URL` still switches to Postgres (Neon free tier) in one line. Cost through Oct 15: under 5 dollars. Reason: one machine, one file to export at data lock, no cold starts while judges click.
- Python 3.12 through uv. Node 26 with npm. Next.js App Router. Playwright with axe-core for end-to-end and accessibility.
- FHIR validator: `validator_cli.jar` on Java 17 in CI (the GitHub ubuntu runner default). Locally through Docker, because this Mac has Java 8 only.
- Implementation guide pin: `hl7-eu/oah` commit `b907cf0` is the current HEAD (2026-06-11). Confirmed today. The package is built from source by SUSHI in CI; the .tgz is never committed because their repo has no LICENSE file.
- Model ids `claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5` match the current model list. Re-checked before the first paid run in Session C.
- Codes: their `TemporaryOahSystem` `present` and `absent` for feature answers, and their codes `morophology`, `invasiveOrganisms`, `LandUse`, `foam`, `riparianVegetation` wherever an item maps. Our local CodeSystem only for `artificial_bank`, `pipe_running` and `cant_tell`. Details go in docs/fhir_mapping.md in Session E.
- Feature answers are CodeableConcepts, never booleans. Their Observation profile allows only CodeableConcept or Quantity values.
- The no-third-party-origin rule covers the study flow, consent through end screen. The rung 2 map pin needs a tile server, which is declared in docs/DATA_HANDLING.md.
- The study database is wiped exactly once, at launch, by `scripts/wipe_for_launch.py`, which appends the wipe to docs/deviations.md itself.

## Sessions

Each session ends with a proving command. Its output is pasted into docs/notes/session_<letter>.md. Estimates assume one evening of about four to five hours.

### Session A, Sun Sep 20, tonight, about 5 hours

Goal: backend and analysis for the usability test, with placeholders that are easy to swap.

Order:
1. Scaffold: uv project; `apps/api`, `core`, `content`, `evals`, `results`, `scripts`, `fhir`, `docs`; Makefile with `dev`, `check`, `preflight`; GitHub Actions running `make check`; `.env.example`; README stub with the section 12 headings; docs/THIRD_PARTY.md; docs/DECISIONS.md; docs/deviations.md (empty).
2. Content: `content/features.yaml`, `content/lessons/<feature>.yaml`, `content/regions/california-bay-area.yaml`, `content/approved_sentences.yaml` (schema plus an empty list), `content/locales/en.json`, `content/glossary.yaml`. App-mirroring items are pre-filled from the app's public text with `verified_against_app: false`. `photos/manifest.csv` with 40 labelled gray placeholder rows and files. `core/content_loader.py` with every fail-loud check from section 6.
3. API: SQLModel tables `session` and `response`; allocator for k arms, permuted blocks of 4, stored seed; the six endpoints from section 6; export with no identifier columns; counts endpoint.
4. Analysis: `evals/make_synthetic_sessions.py` (no effect, real gain, yes bias); `evals/usability_analysis.py` (bootstrap, permutation test, Hedges g, sensitivity checks, refuses real data before lock, refuses to run without the `prereg-v1` tag or with a changed plan file); `evals/power.py`.
5. Gate: `core/gate.py` with the `Flag` model and the fuzz test using hypothesis; record builder that accepts human answers only.
6. Sweep: `evals/model_sweep.py` against a fake client; `results/model_pass_table.json` from the fake run, labelled `real: false`.
7. Claims: `scripts/verify_claims.py`; `docs/analysis_plan.md` word for word from section 7.

Tests that must pass: arm balance within blocks; lesson and test photos disjoint by hash and scene_id; test set is 16 with 2 present and 2 absent per feature; idempotent responses; export has no identifier columns; counts endpoint returns counts only; analysis recovers a planted effect, rejects about 5 percent under no effect, shows no gain under yes bias; analysis refuses real data without the tag; gate fuzz; verify_claims passes on the stub.

Proving command: `make check` green locally and in CI, then `uv run python evals/usability_analysis.py --synthetic all` prints the three results tables.

Not tonight: UI beyond a health page, FHIR, uploads, the checker, any call to OneAquaHealth systems.

### Session B, Mon Sep 21, about 4 hours

Goal: the section 6 flow as a Next.js PWA, deployed.

Build: consent screen with version stamp; warm-up; assignment call; lesson cards with progress bar and per-screen seconds; 16-item test with Yes, No, Can't tell and glossary tooltips; end screen with per-feature score, share link and the prior-experience question; `/demo`; `/health`. English strings from `content/locales/en.json`. axe-core inside Playwright.

Deploy: Fly app for the API with a volume; Vercel project for the web; environment variables; `make preflight --remote` smoke mode against the public URL.

Proving command: `npx playwright test` green for both arms on a phone viewport including the third-party request check, then the public URL completes one QA session flagged `is_test` from Alex's phone.

### Session C, Tue Sep 22, about 4 hours, needs Rachel's photos and labels by 19:00

Goal: real content in, plan frozen, tag, real model run.

Build: swap photos and copy; run the loader; Alex's second labels entered before he sees Rachel's; `results/key_agreement.json`; remove any photo either labeller called ambiguous; `scripts/freeze_key.py`; freeze the four question wordings in docs/analysis_plan.md; dry run with three friends on their own phones; fix what confused them; wipe and log the wipe; `make preflight`; commit; tag `prereg-v1`; print the plan's SHA-256 for Alex to post; run `evals/model_sweep.py` for real through the batch API; commit results and cost log, failures included.

Proving command: `make preflight` prints every check passed; `git show prereg-v1 --stat`; `uv run python scripts/verify_claims.py` passes; `results/model_pass_table.json` has `real: true`.

### Launch, Wed Sep 23 morning

Alex posts the link. From now until lock, the only study number anyone looks at is `GET /api/test/counts`.

### Session D, Wed Sep 23 and Thu Sep 24, about 3 hours each

Goal: the guided creek check and the follow-ups.

Build: `content/form.yaml` in the app's order from Alex's screenshots; `content/followups.yaml`; `core/followups.py` as a pure function with the two-question cap; rainfall client for Open-Meteo with caching, attribution and the 72 hour, 2.5 mm rule in config; guided check UI, one question per screen, one-handed; analyst view of one record showing each answer beside the observer's per-feature score and the checks that ran.

Proving command: pytest passes one test per follow-up rule plus the cap; a Playwright run files one creek check end to end on a phone viewport and opens the analyst view.

### Session E, Fri Sep 25, about 5 hours

Goal: the record in FHIR, validated, mirrored.

Build: docs/fhir_mapping.md first; `fhir/ig.lock`; FSH for our CodeSystem, both Questionnaires, the Practitioner qualification and our Organization; `core/fhir_emit.py`; SUSHI and the validator in CI; our store of validated JSON; sandbox mirror with conditional creates, `meta.tag`, `fhir/sandbox_ledger.jsonl`, `scripts/repush_sandbox.py`; Postman collection; the Library entry; health card from approved sentences only; quick check and timeline.

Proving command: `make check` runs FHIR validation with zero errors; `uv run python scripts/repush_sandbox.py --dry-run` lists what would be written; one real push; then a GET of our Provenance by tag from the sandbox returns it.

### Session F, Sat Sep 26, about 5 hours

Goal: the checker that can only ask, the benchmark, freeze.

Build: vision checker limited to passed features and one follow-up slot; `evals/benchmark.py` with per-feature accuracy and Wilson intervals; `evals/agreement.py` with kappa on a 50 photo overlap; `evals/ablation.py`; adversarial photo test; rotate new photos into the test pool; demo polish; accessibility pass; freeze at night.

Proving command: `make check` green; `results/benchmark.json` and `results/ablation.json` committed; the adversarial test passes.

### Session G, Sun Sep 27 after the 18:00 PDT data lock, about 4 hours

Goal: the truth on the first screen.

Do: export the response table; run `evals/usability_analysis.py` once on real data; generate the README table from `results/`; `verify_claims`; README in the section 12 shape; docs/devpost.md; architecture diagram in their five pipeline stages; the One Digital Health and FAIR box; known weaknesses.

Proving command: `uv run python scripts/verify_claims.py` passes with zero hand-edited numbers; `git diff --stat prereg-v1 -- docs/analysis_plan.md` is empty or every change appears in docs/deviations.md.

### Mon Sep 28 to Wed Sep 30

Mon: record and edit the video; full dry-run submission by midnight. Tue: fixes only, after 19:00. Wed: repo public, incognito check, submit by 18:00 PDT.

## Inputs and latest workable dates

| Input | Who | Wanted by | Latest without moving launch or lock |
|---|---|---|---|
| About 40 photos per the section 16 shot list, originals kept, spot and date noted | Rachel | Tue Sep 22 12:00 | Tue Sep 22 19:00 |
| Gold labels for the 16 test photos, blind, from written definitions | Rachel | with the photos | Tue Sep 22 21:00 |
| One rule of thumb per feature with a source, and the four question wordings | Rachel | Tue Sep 22 12:00 | Tue Sep 22 21:00, frozen at the tag |
| Bay Area invasive list checked against the Cal-IPC inventory | Rachel | Tue Sep 22 12:00 | Tue Sep 22 19:00 |
| Approved health and ecology sentences after reading the indicator factsheets | Rachel | Fri Sep 25 | Sat Sep 26 12:00 |
| Independent second labels for every test photo | Alex | Tue Sep 22 evening | Tue Sep 22 22:00 |
| Community account, one real app assessment, screenshot of every screen | Alex | Mon Sep 21 | Tue Sep 22 19:00 for the four test items; Wed Sep 23 for form.yaml |
| Consent contact email | Alex | Mon Sep 21 | Mon Sep 21 18:00 |
| Vercel account and Fly.io account with a payment method | Alex | Mon Sep 21 | Mon Sep 21 18:00 |
| ANTHROPIC_API_KEY with a few dollars of credit, in .env only | Alex | Tue Sep 22 | Tue Sep 22 19:00 |
| Check the Devpost Create Project form for the Team required flag | Alex | tonight | Sun Sep 27; adding Rachel as a teammate fixes it either way |
| The spike FSH and sandbox_write_test.sh from the planning chats, if they exist | Alex | any time | Fri Sep 25 18:00 |
| Five lines of notes on their AI image model video | Alex | Sat Sep 26 | Sun Sep 27 |
| Recruiting through lab, class, club and creek groups | Alex | Wed Sep 23 08:00 | continuous until Sun Sep 27 18:00 |
| One creek visitor on camera taking the two-minute test | Both | Sun Sep 27 | Mon Sep 28 15:00 |
| Permission from ENORA for their site list | Alex | optional | never required; we ship without it |

## Cut order if a session runs late

1. Rung 4. It was never part of the score.
2. Rung 3 ablation and the 150 photo benchmark. Keep the 16 item model comparison, which is what Track 3 needs.
3. Rung 2 quick check and timeline.
4. Rung 2 sandbox mirror. Keep local validated records and the Postman collection.
5. Never cut: consent, the gate, preflight, the tag, verify_claims, the README first screen.

## Risks

- Photos arrive late: the launch slips one day per day late. The lock does not move, so the sample shrinks.
- Recruiting falls short: below 20 completed sessions per arm the result is descriptive and the first screen says so.
- Another team wipes the sandbox: repush from our store. The ledger makes it a one-command fix.
- Every vision model fails every feature: the checker ships with zero flags and the README says where AI should stay quiet. That is still a Track 3 result.
- The Devpost form refuses a one-person team: add Rachel as a teammate before Sep 28.

## Proposed changes to the brief

Each with the reason in a line. None is applied until Alex approves.

1. Use their codes where they exist, ours only where they do not. Their value set already has `present` and `absent`, and codes for channel morphology, invasive organisms, land use, foam and riparian vegetation. The "same value sets as lab data" sentence then holds word for word.
2. Feature answers as CodeableConcepts, not booleans. Their Observation profile rejects any value that is not a CodeableConcept or a Quantity.
3. Pre-fill the app-mirroring items from the app's public frontend text, saved at `~/scratch/oah-research/`, with `verified_against_app: false` until Alex's screenshots. It is the app's exact wording in seven languages, it came from a static page and not from `api.enora-oah.eu`, and it saves Alex an evening of typing.
4. Production database: SQLite on a Fly volume instead of Postgres. Eighty sessions do not need a second service, and data lock becomes copying one file.
5. Scope the no-third-party-origin rule to the study flow. A map pin in rung 2 cannot exist without a tile server.
6. Add to rule 10: the sandbox has no StructureDefinitions loaded, so it validates nothing, and today it holds zero Provenance and zero QuestionnaireResponse resources. Our CI is the only validator, and the README's alignment section can say, with the date, that ours are the first citizen records there.
7. Drop the wait for a "Session 5 recording". Only five sessions exist, the fifth ran Sep 16 with no recording posted, and there is no Session 6.
8. Claim wording: another entry, stream-to-clinic, already validates against the OneAquaHealth profiles in CI. We claim the first citizen record whose contributor score travels in Provenance, not the first to validate.
9. Add `scripts/wipe_for_launch.py` so the launch wipe is a command that writes its own deviations entry. A hand-written log line is the kind of number rule 12 forbids.
10. One quiet correction for the video script: the app records foam and colour but has no smell item. Our own quick check may ask about smell; the app does not.
