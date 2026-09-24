# Critic round 01

Highest severity: blocker
Commit: a52de70

A critic subagent that wrote none of the code wrote this round on 2026-09-24 UTC, reading the repo at
a52de70 read-only, the live site with GET requests only, and Alex's two public repositories as the
bar. Its report follows as it came back; what the session did about each finding is at the end.

I shallow-cloned both bar repositories and read them. For Tideline that was the README (260 lines), WRITEUP.md, DEPLOY.md, the seven ADRs and the CI workflow. For BlackBox it was the README (297 lines), docs/ACCEPTANCE.md, docs/JUDGE_SCORECARD.md, docs/PROGRESS.md, .github/workflows/ci.yml, the screenshots, examples/sample-incident/ and evals/results/. I also looked at BlackBox's open PR #1 and its branches. Together they set this bar:
- The answer and a real result come first. BlackBox puts product screenshots at the top, then a "See it work" table from one real graded run at line 38, then "Why trust" at line 58 with a proof link in every row.
- Every proof is a clickable link. BlackBox's README has 57 relative links.
- One keyless `make judge-check`, with its expected output pasted into the README.
- An unedited real run in examples/, plus a live receipt: PR #1, left open.
- Honest limits, and a self scorecard that names the current weakness and the next step for each criterion.
- A tidy repository: two branches, and one open PR, which is the receipt.
- Tideline adds a plain statement of what is and is not deployed, a readable architecture diagram, ADRs, and a WRITEUP of the engineering challenges.

## Where Second Look already meets or beats the bar
- `make judge-check` passed 6 of 6 steps offline with no key in a fresh clone of a52de70 on this Mac. The whole run took about 4 minutes 16 seconds, installs included. It also regraded "28603 values in 26 files ... every one matches", which BlackBox's judge-check does not attempt.
- It has a model card, a data card and a threat model, each row naming the test that fails. Neither bar repository has any of the three.
- README numbers are tied to results/ by claim markers checked in CI. BlackBox's numbers are typed into its badges and tables.
- 11 ADRs, against Tideline's 7. WRITEUP.md has 11 engineering challenges, each with a proving test, the same shape as Tideline's WRITEUP.
- The "Known weaknesses" section and the real vs synthetic table are at least as candid as BlackBox's "Honest limitations".
- It contributed back upstream: hl7-eu/oah PR 5 and issues 6 to 8, all open, matching BlackBox's two upstream PRs.
- The prereg-v1 tag, the analysis plan and the audit head are stamped with OpenTimestamps, and /verify rechecks the chain in the browser. Neither bar repository has anything like it.
- Three Mermaid diagrams, each with accTitle and accDescr, and a CI check that the committed SVGs are fresh.
- The live site passed my GET-only check: 11 pages at 390 px and 8 at 1440 px each returned 200 with no failed request and no console error.
- CI on main was green on the last three pushes.

## Findings

### C01. `make judge-check` prints FAIL on a clean machine: the Quickstart never installs the browser the design check needs
- Severity: blocker
- Where: README.md:502-508 (Quickstart), docs/ACCEPTANCE.md:13 (setup), scripts/judge_check.py:193
- Compared: BlackBox README "For judges" says `make judge-check` needs "no API key, no DataHub, no network service" and pastes the output a judge will see. Its CI (blackbox-datahub/.github/workflows/ci.yml) runs the same keyless steps.
- Evidence: My judge-check run passed only because this Mac already had Playwright's chromium_headless_shell-1243 cached. With `PLAYWRIGHT_BROWSERS_PATH` set to an empty folder, `node scripts/design-check.mjs` exited 1 with "browserType.launch: Executable doesn't exist ... npx playwright install". Run through judge-check itself, `judge_check.step_web(...)` returned `FAIL ['next build ok', 'design-check failed: apps/web/tests/design.spec.ts:1 tap target measurement failed']`. A judge would read that as the app failing its own tap target check. The README Quickstart installs uv, apps/web, worker and tools/diagrams, but no browser. CI does install one (check.yml: `npx playwright install --with-deps chromium`). docs/ACCEPTANCE.md's setup is worse. It runs only `cd apps/web && npm install` and never `(cd worker && npm ci)`. worker's `npm test` needs esbuild from worker/node_modules, so the tests step would fail too.
- Fix: Add `(cd apps/web && npx playwright install chromium)` to README.md:504 and to ACCEPTANCE's setup, and add `(cd worker && npm ci)` to ACCEPTANCE. Have design-check.mjs print "Playwright's Chromium is not installed: run npx playwright install chromium" when the launch fails. To prove it: run judge-check again with `PLAYWRIGHT_BROWSERS_PATH` pointing at an empty folder after the Quickstart.

### C02. The judge scorecard the README links says the AI numbers are still to come, and points at README sections that do not exist
- Severity: blocker
- Where: docs/JUDGE_SCORECARD.md:12, 26, 31, 35, 56
- Compared: blackbox-datahub/docs/JUDGE_SCORECARD.md is dated. Each criterion has "Current weakness" and "Next improvement", kept current: the Stage One note is marked "RESOLVED 2026-08-10".
- Evidence: README.md:536 lists "Our own scorecard, weaknesses included | docs/JUDGE_SCORECARD.md". The scorecard says at :31 "Thin: the model results arrive with the paid run (`uv run python evals/model_sweep.py --real`)." and at :35 "Our mark: strong, with the AI numbers still to come from the paid run." But results/model_pass_table.json says `"real": true`, and results/cost_log.jsonl holds 5017 paid calls. :12 cites "README, The problem" and :26 cites "README, Innovation and practical value". No README heading has either name: the list of `^## ` headings runs from "Numbers at a glance" to "Licence". :56 says "Two minutes, no camera, any phone", while the consent screen says "about four minutes". Last edited in ac20f1f, 2026-09-24 00:15, before the paid-run text reached the README.
- Fix: Rewrite the three stale lines. Point each row at a heading that exists, such as "Why trust a volunteer, and the AI?". Add "no person has taken the test yet" as Impact's weakness. Proving check: a test that every "README, X" in the scorecard names a real README heading.

### C03. The docs contradict each other on recruiting: "Recruitment was dropped" and "no recruited study", while a paid Prolific panel is planned
- Severity: blocker
- Where: README.md:68, README.md:461, README.md:574, docs/submission/JUDGE_QA.md:65, docs/deviations.md:12, docs/JUDGE_SCORECARD.md:17, docs/ALEX_TODO.md:27-28
- Compared: BlackBox says what it did in one voice everywhere, for example "PR publication is wired but opt-in", the same in blackbox-datahub/README.md and docs/ACCEPTANCE.md.
- Evidence: README.md:68: "a paid research panel may add sessions before the lock". README.md:574: "There is no recruited study. Whoever opens the link is whoever opens the link." README.md:461: "Nobody is recruited". JUDGE_QA.md:65, edited in bbef994 on Sep 24: "Recruitment was dropped." deviations.md:12: "Panel members are paid by the panel, not by us, and nobody is recruited by us". ALEX_TODO.md step 3: "By Sat Sep 26 ... launch the panel study. Make a researcher account on Prolific, add about 300 dollars, create the study". Live consent (en.json:12) says panel members "will be paid by the panel". No document mentions ethics review or an exemption (git grep for IRB, "ethics review" and "human subjects": nothing). REVIEW_03's R45 changed line 68 but left :461 and :574 standing.
- Fix: Decide now whether the panel runs, then write one sentence and use it in all seven places. If it runs, something like: "We paid Prolific for up to N sessions; they count in the one pre-registered analysis." Say whether an ethics review or exemption applies. Proving check: a git grep in make check that fails on "no recruited" or "Recruitment was dropped" while PANEL_STUDY exists.

### C04. "Berkeley is a follower city" is stated as fact on the site, in the partner's sandbox and in the upstream PR, and a hand-made visit is described there as citizen data
- Severity: blocker
- Where: content/locales/en.json:278, core/fhir_library.py:71 and :101, docs/ig_proposal.md:3, hl7-eu/oah PR 5 body
- Compared: BlackBox README "What's real vs. synthetic" and "Pointing this at a real stack" say plainly: "we demonstrate on a pipeline we authored, so treat the incident realism as illustrative".
- Evidence: Live /about: "Berkeley is a follower city." The PR 5 body (gh pr view 5 -R hl7-eu/oah): "Hello from the Second Look team in Berkeley, a follower city." The project's own definition (README.md:444) is "a city that adopts the method". Nothing in the repository shows that Berkeley or OneAquaHealth agreed to it. The Library written to their sandbox (fhir/golden/library-second-look.json) says "citizen creek checks from Berkeley, a follower city ... 1 visit records mirrored". fhir/sandbox_ledger.jsonl shows that one visit is `visit-strawberry-creek-1.json`, which README.md:484 calls "example, hand shaped". It went out with only the `second-look` tag and no example tag (the transaction file's tags: `{"code": "second-look", ...}`).
- Fix: Say "run the way a follower city would" in en.json:278, fhir_library.py, ig_proposal.md and the PR body. Make the Library description say the mirrored visit is a hand-made example, and use the allowed conditional update on the Library when their sandbox resolves again.

### C05. No real end-to-end run exists anywhere: "See it work" is hand-shaped, and the live creek has no session, no visit and no record
- Severity: major
- Where: README.md:550-561, docs/devpost.md:98-99, examples/
- Compared: BlackBox's "See it work" (README line 38) is "One autonomous run, graded on 11 machine-checked criteria". examples/sample-incident/ holds the "unedited incident state, full agent transcript, the real patch", and PR #1 is a live receipt.
- Evidence: README.md:552: "from the golden record in this repository. It is an example, hand shaped". Live GET /api/test/counts: all zeros, "completed":0 in both arms, "post_lock":0. Live GET /api/city/strawberry-creek: "visits":0,"spots":0,"needs":[]. The /city page reads "Nobody has checked this creek yet." examples/ holds only mcp/, a transcript from "a throwaway database". The Devpost demonstration field promises "/spot: the record, each answer beside the observer's score ... the health card" and "/city: ... what the creek needs in OneAquaHealth's own measures". A judge can open neither on the live site. The report says "this report makes no claim about people". The product's thesis is about people.
- Fix: Before the lock, run one real creek check at Strawberry Creek through the live site, QA-marked if it must not count, and commit its unedited Bundle and /spot screenshot under examples/real-visit/. Point "See it work" and devpost.md:98 at it. At the least, commit an unedited walk record exported from live /walk/v02 and use that instead of the golden.

### C06. The README never states its result near the top; the report's abstract does, in six sentences
- Severity: major
- Where: README.md:1-135, README.md:550
- Compared: blackbox-datahub/README.md has its screenshots, then "See it work" at line 38 of 297, then "Why trust" at line 58. Tideline's README has its answer and a screenshot on its first screen.
- Evidence: The README is 611 lines, 68 KB, against BlackBox's 297 lines, 26 KB. "Why trust a volunteer, and the AI?" starts at line 135, after a 31-screen gallery. "See it work" is at line 550. The first numbers table (README.md:47-55) crams four models into one cell, and 5 of its 14 data cells say "not asked" or "not measured". The README never says why the plant column is "did not pass" for every model. docs/REPORT.pdf page 1 says it cleanly: "Every model passed built banks, and no model passed plants that do not belong ... the gate dropped 29 of 64 candidate flags ... No study with recruited people has been run".
- Fix: Paste the report's abstract, with its claim markers, under the title. Move "See it work" (with a real run, see C05) above the gallery. Cut the gallery to 5 screens and link the rest from docs/screens/.

### C07. The README's proofs are not clickable: 106 repository paths in backticks, 7 linked documents
- Severity: major
- Where: README.md:143-191, 416-429, 530-537
- Compared: blackbox-datahub/README.md has 57 relative links. Every row of its "Why trust", "Safety envelope" and "For judges" tables links its proof, for example [`tests/test_engine.py`](tests/test_engine.py).
- Evidence: 106 distinct backticked strings in README.md are existing repository paths. Only 9 relative links exist: DEPLOY, WRITEUP, DATA_CARD, MODEL_CARD, REPORT.pdf, THREAT_MODEL, the adr README and two photos. The "For judges" proof table (README.md:530-537) links none of its six targets: docs/ACCEPTANCE.md, fhir/golden/visit-strawberry-creek-1.json, results/, docs/ARCHITECTURE.md, docs/JUDGE_SCORECARD.md and docs/video_script.md.
- Fix: Wrap each backticked path that exists as [`path`](path), with the test anchor dropped from the link target. Start with the For judges, Why trust, What the AI cannot do and Three properties tables. The existing link check keeps the links alive.

### C08. The Devpost gallery ends on the empty city page, captioned as showing OneAquaHealth's measures
- Severity: major
- Where: docs/devpost.md:173, docs/screens/city.webp
- Compared: BlackBox's screenshots (docs/screenshots/03-rootcause.png, 04-resolved.png) show the result state, "verified repair (32/32, real diff, git branch)".
- Evidence: devpost.md:173 says "5. `docs/screens/city.webp`: what the creek needs, in OneAquaHealth's own measures." The image reads "0 visits at 0 spots" and "No measure is shown yet ... nobody has approved one". docs/screens/walk-city.webp does show "Find and fix leaking or wrongly connected sewers ... OneAquaHealth Policy Brief (2026), page 9". This is related to R27, which covers the README row and alt text but not the Devpost gallery.
- Fix: Swap gallery image 5 for walk-city.webp, retaken after the R32 double-count fix, or for a capture of make demo-offline's /city labelled as demo data.

### C09. On the live site, a judge can reach no evidence: the root does not link /judges, no page links the code, and /how-we-know shows no number
- Severity: major
- Where: apps/web/app/page.tsx, apps/web/app/about/page.tsx, apps/web/app/judges, apps/web/app/how-we-know/page.tsx
- Compared: BlackBox's "For judges" table maps each proof to its artifact. Its 45-second path links screenshots, the result, the PR, the evals and judge-check in order.
- Evidence: The live root links only "About" and "Find out in two minutes", and /about adds only Privacy, How we know, Photo credits and Accessibility. The repository and Devpost's "Live link" both point at that root. In the source, only /demo and /city link /judges. No live page links github.com/alejandro-publius/second-look, the model card, the report or results/. /judges is ten bare links, only one with a line of text, and no time for any of them. "How we know it works" says "Every number we show comes from a script" and then shows no number: no pass table, no counts. /verify says "In a copy of the code, these commands..." but does not link the code.
- Fix: Add a "For judges" link to the landing page and /about. On /judges, give each door one line saying what it proves and how long it takes, and add links to the repository, the README's For judges section, REPORT.pdf and MODEL_CARD. They will resolve on Sep 30. Render the pass table and the counts from results/ into /how-we-know at build time.

### C10. The judge Q&A still says the key came from Alex "from written definitions", leaving out that the labels came from a Claude chat
- Severity: major
- Where: docs/submission/JUDGE_QA.md:16
- Compared: BlackBox's docs/ACCEPTANCE.md "Honest limitations" states each limit the same way everywhere it appears.
- Evidence: JUDGE_QA.md:16 (edited in bbef994): "One labeller, Alex Velazquez, from written definitions and from what each photo's own source says about it." DATA_CARD.md says: "The picks, and the label column in them, came from the planner's picks file. The planner is a Claude chat". The models graded against this key are Claude models. REVIEW_03's R16 covers README.md:567 and the report, not this answer.
- Fix: Replace Q3's answer with the DATA_CARD wording: the key came from the picks file made with the planner, there is one labeller and no blind label yet, so read accuracy as agreement with this key.

### C11. The README's test counts are stale, and nothing ties results/test_counts.json to the tree
- Severity: minor
- Where: README.md:469-470, WRITEUP.md section 3, results/test_counts.json
- Compared: Tideline states "98 tests" and "36 tests" beside the commands that print them.
- Evidence: results/test_counts.json was measured at 95f1c50. At a52de70, `uv run pytest --collect-only -q` sums to 1908, where the README says 1906. `worker npm test` prints "tests 14 ... pass 14", where the README and WRITEUP say 12. golden.test.ts gained two upload tests in bbef994. judge-check itself printed "worker: pass 14" next to a README that says 12. Makefile:130: make test-counts is "Not in make check".
- Fix: Run make test-counts and make render-readme as the last step before submission. Have judge-check warn when its counts differ from results/test_counts.json.

### C12. The only cost in the README is 51.3 USD per 100 frames, which is four models times four questions times three runs
- Severity: minor
- Where: README.md:54
- Compared: BlackBox's JUDGE_SCORECARD names cost and latency per run as a weakness to publish.
- Evidence: README.md:54: "Cost per 100 frames | not asked | 51.3 USD, with direct calls at the full price, four models". From results/cost_log.jsonl (footage purpose), one call cost 0.22 cents on Haiku 4.5, 0.43 on Sonnet 5, 0.96 on Opus 5.5 and 2.32 on Fable 5.1. A judge scoring feasibility sees 51 cents a frame.
- Fix: Add a row, "One checker question: 0.2 to 2.3 cents, by model (results/cost_log.jsonl)", and say what the 51.3 figure multiplies.

### C13. The accuracy table has no baseline, so 31 to 34 of 48 cannot be read
- Severity: minor
- Where: README.md:50, docs/MODEL_CARD.md benchmark table
- Compared: BlackBox runs a "No-incident control" and a "Bad-repair rejection" beside its positive run (blackbox-datahub/README.md, Evals).
- Evidence: Each feature has 2 present and 2 absent photos, so always answering No scores 24 of 48. All four models scored 0 of 12 on plants, because the instruction says can't tell when no stream is visible (MODEL_CARD). Without plants, Haiku 4.5 is 31 of 36. Neither figure is in the table.
- Fix: Have evals write an "always No" row and a "without plants" total into the benchmark file, and show both with claim markers.

### C14. The sandbox proof a judge is handed is a curl to a host the README says does not resolve
- Severity: minor
- Where: README.md:560
- Compared: BlackBox points at committed evidence, such as examples/sample-incident/incident_state.json with `"via": "datahub-mcp-server"`, not a live call that may fail.
- Evidence: README.md:560 gives `curl ... https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466`. README.md:573 says "Their sandbox's name, sandbox.hl7europe.eu, stopped resolving on Sep 23". The saved read-back is docs/notes/sandbox_library.md, with a screenshot in docs/notes/sandbox-library.png.
- Fix: Cite the read-back and the screenshot first, and mark the curl "when their name resolves again (hl7-eu/oah issue 8)".

### C15. The repository a judge opens on Sep 30 carries working clutter
- Severity: minor
- Where: scripts/go_public.py:9, GitHub PRs and issues, docs/
- Compared: BlackBox has 2 branches, and its only open PR is the receipt. Its process log, docs/PROGRESS.md, is a neutral log.
- Evidence: 8 open Dependabot PRs; #14 (react-dom) and #16 (opencv 5.0) fail CI. 17 branches: takeover, polish, harden, finish, depth, p27/integrate, ci-main, ci-depth and the Dependabot ones. Open issue #4, "Status: Second Look", starts "For Alex, Sep 24". go_public.py removes only docs/internal. So docs/ALEX_TODO.md ("add about 300 dollars", "Copy that key and your API key to your password manager"), docs/HANDOFF_NEXT.md, docs/SUBMISSION_CHECKLIST.md and PLAN.md stay public. SUBMISSION_CHECKLIST says five_headers checks README.md, but submit_check.py:194-200 reads docs/devpost.md.
- Fix: Merge or close the Dependabot PRs, grouped in dependabot.yml. Delete merged working branches. Close issue 4. Add those four files to go_public's removal list, or move them under docs/internal.

### C16. The first architecture diagram is too wide to read at README width
- Severity: minor
- Where: README.md:201-275, docs/diagrams/system-map.svg
- Compared: BlackBox's single README diagram, drawn with the same Mermaid CLI 11.17.0, is 2281 by 1646. Tideline's is a 9-node flowchart.
- Evidence: system-map.svg's viewBox is 3742 by 2263, with 32 labelled edges. At an 830 px README column that is a scale of 0.22, so a 16 px label becomes about 3.5 px. My render at 830 px shows unreadable labels.
- Fix: Show a 5 to 7 box Train, Check, Verify, Record, Act loop in the README, and move the full map to docs/ARCHITECTURE.md.

### C17. The live site is behind the commit under review
- Severity: minor
- Where: https://second-look-79t.pages.dev/verify, /t?src=other
- Compared: BlackBox's docs/ACCEPTANCE.md dates the day every gate was "checked against the running system".
- Evidence: Remote main is 183066d, and a52de70 is five local commits ahead. Live /verify shows "Waiting for a Bitcoin block" 9 times and "Last asked at 2026-09-24T07:50:13Z", while results/ots.json says `"confirmed": 3` in block 968372. Live consent omits "the kind of link you came from", which en.json:10 at a52de70 has.
- Fix: Deploy, then run `SITE_URL=... node apps/web/scripts/live-readonly.mjs` and a /verify check that no proof says waiting.

### C18. Four of five README badges link nowhere, and one is a fixed green image
- Severity: minor
- Where: README.md:14-17
- Compared: every BlackBox badge links to its evidence, for example "invariants 32/32" to evals/results/ and "flagship eval 11/11" to evals/results/run_0007.json.
- Evidence: `![tests: make check](https://img.shields.io/badge/tests-make%20check%20green-brightgreen)` can never go red. The licence, FHIR and guide badges have no link target. Only the check workflow badge links.
- Fix: Drop the fixed tests badge, since the workflow badge says the same live. Link the others to LICENSE, results/fhir_validation.json and fhir/ig.lock.

### C19. The technical report has no figure, and its tables split file names mid-word
- Severity: minor
- Where: docs/REPORT.pdf pages 1 to 7, scripts/build_report.py
- Compared: BlackBox's docs/ARCHITECTURE.md carries its diagram. Its README shows five screenshots beside the text.
- Evidence: pypdf finds 0 images in the 7 pages, and no diagram label such as "TRAIN" appears in the text. Page 5's Where column prints "content/form.yam l" and "core/fhir_emit.p y". One row there says "this README" inside the PDF.
- Fix: Embed the three SVGs and three screens. Set `word-break` in the code cells to break only at "/". Change "this README" to "the README".

### C20. The README describes judge-check in prose but does not show what a judge will see
- Severity: minor
- Where: README.md:508
- Compared: blackbox-datahub/README.md pastes the five-line "BLACKBOX JUDGE CHECK" block with test counts.
- Evidence: My run printed six PASS lines ending "judge-check: 6 of 6 steps passed, offline, with no key". The tests line shows only dots (known R47), so no count appears.
- Fix: After R47's fix, paste the six-line summary under the Quickstart, with its counts as claim markers.

### C21. A public ADR reads as a private remark
- Severity: cosmetic
- Where: docs/adr/0008-open-footage-no-creek-visit.md, Context
- Compared: Tideline's docs/adr/0007-event-driven-anomaly-detection.md states context in neutral terms.
- Evidence: "the plan had been for Alex to film at a creek. He was not going to."
- Fix: "Filming at a creek was dropped for time."

### C22. CI is one job named "check", so a red run does not say what broke
- Severity: cosmetic
- Where: .github/workflows/check.yml
- Compared: blackbox-datahub/.github/workflows/ci.yml has five named jobs (backend-tests, lint, pipeline-invariants, frontend, secrets-scan), and its header says each runs with no secret.
- Evidence: One job runs make check, make e2e and the Worker e2e in about 11 minutes.
- Fix: Split it into named jobs, such as python, worker, web e2e, fhir and secrets, or at least give each step a `name:`.
