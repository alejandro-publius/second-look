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

## Phase 3, integration, 2026-09-21 01:00Z
- What: all eight workstreams merged. docker compose serves web, API and Postgres the way production will. The API image now carries results/ and the FHIR goldens, with a .dockerignore so the validator jar and the guide checkout stay out. The container migrates on start and runs without access logs behind proxy headers.
- Proof: `scripts/smoke.py` printed "landing 200 in 84 ms, api health ok, db rows 1 then 2"; a full 16 item session through the live API returned 8 of 16 with a contributor token and counts by arm and source; export without a token answered 404; `/api/fhir/validation` answered 200 with ig_commit b907cf0, 0 errors; `/api/two` answered ok with our Strawberry Creek observation beside their Almyros dissolved oxygen result; `npx playwright test` 28 passed on a phone viewport; `make check` green; 488 tests.
- Surprises: the stale Postgres volume from Phase 1 held tables the migration also creates, so the API crashed on start until the volume was recreated. The FHIR validation route answered 404 in the container purely because results/ was not in the image.
- Decisions: web stays on 3000 for compose and production, Playwright keeps its own server on 3100; make e2e builds before it tests.
- Next: Phase 4, the adversarial review, then fix what it finds.

## Phase 4 and 6, review, fixes and report, 2026-09-21 01:35Z
- What: an agent that wrote none of the code attacked the running stack and wrote docs/reviews/REVIEW_01.md. Eight findings broke a hard rule, lost data or blocked launch and were fixed with tests; the rest are deferred in that file with one line each. Phase 5 extras and the design pass were skipped on instruction.
- Proof: `make check` green, 493 python tests, 28 Playwright tests; `preflight` 115 failed, all 115 human; `submit-check` 3 failed and they are the expected three; gitleaks clean against a fingerprint file that names every fake value.
- Surprises: the review defeated the data lock with two test flags, harvested the whole answer key from judge mode in sixteen requests, and found a free text spot name published into the FHIR narrative. None of that was visible from inside the workstreams that wrote it.
- Decisions: one browser keeps one arm; the record carries a hash of the contributor token, never the token; a pass table from the fake client licenses nothing anywhere.
- Next: Rachel's photos, blind labels, merge, freeze the key, tag prereg-v1, then preflight must print 0 failed.

## Update 14 phases 1 and 2, launch and cleanup, 2026-09-22 05:45Z
- What: main carries the dropped study in the plan before the tag, is tagged prereg-v1 and pushed, with the plan_tagged audit entry and docs/notes/plan_hash.md. The API Worker is deployed. On depth the Update 13 cleanup was verified done (14 approved sentences, the policy brief source, the morophology line, Cloudflare only, docs/internal), the stale analysis plan was replaced by the tagged one, and every promise of a recruited result left README.md and PLAN.md.
- Proof: `make preflight-launch` prints 17 run, 15 passed, 0 failed, 17 notes. `make audit-verify` prints 3 entries, chain intact, last hash 3d3cbb4d. `git show prereg-v1 --stat`.
- Surprises: the live Pages build predates the consent contact email, so the deployed smoke test fails on it; the web deploy that fixes it, and emptying the live D1 table, are both outside what this terminal may do on its own.
- Decisions: Update 14 lives under docs/internal/updates; no key means the fake client everywhere; depth takes main's tagged plan verbatim.
- Next: phase 3, the AI on the 16-photo test and on open creek footage.

## Update 14 phases 3 to 8, cloud takeover by prompt 18, 2026-09-22 21:50Z
- What: CI green on main and depth (PRs #2, #3); `make go-public` prints the Sep 30 steps and changes nothing; docs/JUDGE_SCORECARD.md and docs/ACCEPTANCE.md; `apps/web/scripts/record-clips.mjs` and docs/video/SHOTLIST.md. The kits (voice script, teleprompter, creek plan, Devpost paste, judge questions, upstream) are on `finish`.
- Proof: `make go-public` lists 15 live files that point at docs/internal; `make submit-check` fails only on video_link and repo_public; a trial `node apps/web/scripts/record-clips.mjs` wrote six clips.
- Surprises: evals/models.yaml and evals/pricing.yaml still say unconfirmed although docs/notes/model_ids.md records the check on 2026-09-21, so the paid run refuses until someone flips them. That is Alex's call, left for him.
- Decisions: no key and no Mac here, so no paid run, no footage download, no deploy, no merge into main. Those are commands in the status issue.
- Next: Alex flips the two flags and runs `uv run python evals/model_sweep.py --real`; then the footage search, /walk, the merge and deploy in the hosting.md order, on the Mac.

## Update 14 phase 3, the Mac's part, by prompt 15, 2026-09-23 06:00Z
- What: open creek footage searched (68 candidates), picked by rule over eight rounds, screened by Apple Vision and by eye: 46 frames from 5 videos in 3 countries. /walk: three walks, every second screened, the record built on the phone and never sent. evals/footage.py built and run on the fake client. The branch was merged with the cloud takeover (7f2b1d5).
- Proof: `uv run python evals/footage_pool.py` prints 68 candidates, 5 videos, 3 countries, 46 frames, 3 walks; `make fhir-validate` 14 files, 0 errors, 2 of them walk records; `cd worker && npm test` 10 passed.
- Surprises: the OpenCV screen let through a talking head, title cards and a hiker; the stopped session's only labelled video was that talking head. YouTube began answering with a bot check. The validator caught two Locations with one fullUrl in the walk Bundle, and check_bundle now catches that too.
- Decisions: no plant label from a description; three walks, not four; the model gate flags stay Alex's; the batch custom ids are positional.
- Next: design review 02's safe findings, the Playwright specs, the screenshots.

## Update 14 phases 4 and 5, 2026-09-23 06:40Z
- What: README in the tier 3 shape under the organizers' five headers, every number rendered from results/ and checked; the scorecard and acceptance lists joined with the cloud's; design review 02's safe findings fixed by six agents in their own worktrees; every screen photographed again with the walks.
- Proof: `make check` CHECK GREEN; `npx playwright test` 55 passed, 0 failed; `uv run python scripts/verify_claims.py` 10 claims match.
- Surprises: the merge emptied sw.js (a one line write that truncated before it read), and nothing noticed until a Playwright spec that CI does not run; the creek check sent "changed" for the rating check, which both servers refuse.
- Decisions: the test flow findings and the landing labels are left alone; "Not sure" stays in seven check questions because it is the official app's text.
- Next: the Devpost fields, the gates, the video.

## Update 14 phases 6 to 8, 2026-09-23 07:00Z
- What: the merge proof; the sandbox checked and the re-push job installed; recordings and a rough cut with a scratch voice; docs/devpost.md current and checked; make go-public prepared; gitleaks clean with reasons.
- Proof: `git diff --stat prereg-v1..HEAD` over the test flow and study code is empty; `make submit-check` fails only on video_link and repo_public; `make video-rough` 4:28 with cards, 3:46 without.
- Surprises: Playwright pads a page into a larger video; submit-check had never run gitleaks since Sep 21.
- Decisions: production waits for Alex's QA key and his word on timing; no video file is committed.
- Next: Alex's page, docs/ALEX_TODO.md.

## UPDATE_19: the merge, 2026-09-23 19:50Z
- What: pull request #5's missing files brought in and #5 closed; the QA key set; the D1 tables and the Worker deployed; depth merged into main; Pages deployed with the API on the same origin; Early Hints restored for the landing page and the poster.
- Proof: CI green on depth (8cdc5d2) and on main; `git diff --stat prereg-v1..HEAD` over 17 paths empty, 16 of 16 study functions identical; `live-check.mjs` with the QA key passed three times against production, each sitting stored as a test; `live-readonly.mjs` 11 of 11; counts 2 randomized, 1 completed before and after; `/demo` says Judge mode opens on Sep 28; 15 of 15 ledger resources on their sandbox answer 200.
- Surprises: a judge answer in #5 cited a results file that says the opposite; the read-only check waited for a row /two no longer draws; Pages dropped the Early Hints when Functions arrived; their sandbox does not answer the Worker.
- Decisions: the when-Alex-is-back list and the creek plan merged into depth's existing files; the throttled first screen restored through _headers, not by touching the test photos.
- Next: docs/ALEX_TODO.md step 1, then the model run.
