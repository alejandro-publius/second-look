# Critic round 08

Two critic subagents that wrote none of the code were to write this round on 2026-09-24 UTC, one on the repository and one on the live product, and each finding above cosmetic was then checked by a separate skeptic subagent. The live product critic stalled on all six attempts (no progress for three minutes each) and returned nothing, so this round covers the repository only; the live product is covered again in round 09. The repository critic's round follows as it came back.

Highest severity: major
Commit: 86e3c0c

The repository critic: I read CRITIC_07 first, then the DECISIONS lines dated 2026-09-24 and the diff from bef7015 to 86e3c0c (5 commits, 32 files). An earlier interrupted pass of this same task had left a fresh clone of 86e3c0c in my scratch folder. I checked that it was clean, at 86e3c0c, with pushing turned off, and used it. I also made a second fresh clone and ran the Quickstart setup line word for word, with Playwright's browsers going into an empty folder: setup took 30 s, and `make judge-check` then printed 6 of 6 PASS in 248 s (the first clone gave 26 s and 249 s). In a clone I ran `make verify-claims`: the README had 114 claims and 40 alt texts, and all 12 files matched. I also checked the 108 `path::test` citations and the 219 relative links in the README, WRITEUP, ACCEPTANCE, JUDGE_QA, MODEL_CARD, JUDGE_SCORECARD and both examples, and ran `make mutation` at 86e3c0c (151 s). I scanned every public .md for headings inside a `<details>` fold, and listed every number in the README that sits outside a checked marker. I rendered all 8 pages of docs/REPORT.pdf with PyMuPDF and read each one. With gh, using GET only, I read the CI runs for 86e3c0c on main and depth, the main job log, the README as GitHub renders it on main (the html media type, main = 86e3c0c), and the latest commits and CI of Tideline (793560e) and BlackBox (b72a32c). For both bar repos, shallow clones are in my scratch folder. I counted visible README words the same way for all three. On live hosts I sent one GET to the MCP API's /health (200) and nothing else. No request went to either forbidden host, and I ran no npm audit. The only non-GET traffic was npm ci's built-in audit inside the Quickstart line itself. I checked every finding a second time against the file, the log or GitHub's rendering before keeping it.

## Round 07, checked again
- J01: Fixed. Runs 36039948800 (main) and 36039942769 (depth) at 86e3c0c both finished success at 18:27Z. The main log shows CHECK GREEN, verify-claims passing on WRITEUP.md (16 claims) and docs/ACCEPTANCE.md (1 claim), make reproduce, Playwright 112 passed with 2 skipped, and Worker e2e 14 sections. WRITEUP.md:67 now says 125, and ACCEPTANCE.md row 18 says 14. ACCEPTANCE joined RENDERED_DOCS, and test_every_doc_with_a_rendered_number_is_rendered_and_checked guards it. JUDGE_QA Q19 names the red stretch from 0326e78 to bef7015. Issue #4 is left as the known limit says.
- J02: Fixed. All 8 pages of REPORT.pdf were rendered: the risk table on pages 1 and 2 and the surfaces table on page 6 print as tables, and no page's text holds "|---|".
- D06: Partly. The overall length is a recorded decision and not reported. By my count, visible words are 4,473 with the accidental fold in K01, or 4,822 once it is closed; BlackBox has 2,459 and Tideline 2,802. Specific repeats remain and are reported again below at cosmetic. The D06 cut also moved the mutation row under a sentence that is now untrue, which is reported as K04.

## Where Second Look already meets or beats the bar
- CI is green at this commit on main (run 36039948800) and depth (run 36039942769). The main log shows make check printing CHECK GREEN, make reproduce, Playwright 112 passed with 2 skipped, and the Worker end to end at 14 sections. Tideline's and BlackBox's latest main runs are green too.
- The Quickstart holds in two fresh clones of 86e3c0c. Setup took 26 s and 30 s, then make judge-check printed "6 of 6 steps passed, offline, with no key" in 249 s and 248 s, with 28603 values regraded and the tree clean afterwards. BlackBox's Quickstart needs Docker, DataHub and an Anthropic key.
- Every claim I checked is backed. make verify-claims matched 114 README claims and 40 alt texts, and all 12 files it checks passed. All 108 path::test citations in the judge docs exist, and all 219 relative links resolve. No measured number in the README sits outside a checked marker.
- The report now reads as a report. All 8 pages of REPORT.pdf render their tables as tables, with no raw pipe text.
- The weak point of the footage run is stated where a judge meets it. examples/footage-flag says what the kept frame shows and that no other model that passed built banks said yes there. Known weaknesses says 32 of the 35 kept flags ask nothing. Both are in REPORT.pdf page 7 too.
- The J01 class of error now has a guard. A test fails when a doc with a rendered number is left out of make render-readme or make verify-claims, and JUDGE_QA Q19 says plainly when CI was red and why.

## Findings

### K01. An unclosed fold in the Gallery hides "Why trust a volunteer, and the AI?" and "What the AI cannot do" on GitHub
- Severity: major
- Where: README.md:91 opens the fold "Two lesson photos with their marks, and the licences of the photos in the screens", and the fold closes only at README.md:146. Also README.md:40 and docs/JUDGE_SCORECARD.md:26. Introduced in 85be041.
- Compared: Neither BlackBox's nor Tideline's README uses a single fold. BlackBox's "Why trust the agent?" is a visible H2 at line 58, right after See it work.
- Evidence: In the raw README, `<details>` is at line 91, `## Why trust a volunteer, and the AI?` at 105, the risk table's own fold at 113 to 133, and `## What the AI cannot do` at 135. The only `</details>` that closes line 91 is at 146. The 85be041 diff added the `<details>` above the lesson photos but put its `</details>` after the What the AI cannot do table, instead of before line 105. I fetched GitHub's own rendering of the README on main (86e3c0c) with a GET. Both H2 headings, the RHS quote, the 14-row risk table and the 6-row limits table all sit inside the lesson-photos summary: the rendered stretch from that summary to "The gate, the heart of it" holds one `<details` and two `</details>`. So a judge scrolling the README sees Numbers at a glance, then Gallery, then one closed fold about lesson photos, then The gate. README:40 tells judges that *The problem* and *Innovation and practical value* "are under Why trust a volunteer, and the AI?", and JUDGE_SCORECARD.md:26 sends the innovation row to the same section. The done-list check reads raw headings, so the section order still passes. REPORT.pdf is not affected, because build_report unfolds the folds. A scan of every public .md found no other heading inside a fold.
- Fix: Move the `</details>` from README.md:146 up to just before `## Why trust a volunteer, and the AI?`, after the licence paragraph at line 103. Add a test that fails when any `## ` heading in a tracked .md sits inside an open `<details>`, and make sure the test goes red with the line put back where it is now.

### K02. The first architecture diagram shows flags flowing into the record
- Severity: minor
- Where: README.md:189 (the loop, the first diagram under Architecture); docs/diagrams/loop.mmd:11, drawn into docs/diagrams/loop.svg
- Compared: Second Look's own system map (README.md:255) labels the edge into the record builder "human answers, ratings, follow-up answers". BlackBox's diagram labels its gate edge "accepted / rejected", which matches its text.
- Evidence: The loop's edge reads VERIFY -- "answers, score, flags" --> RECORD. Gate step 7 (README.md:158) says build_record "has no parameter that could carry a flag". README.md:278 says the model "has no path to the store". core/gate.py:242 build_record takes visit_id, spot, observer, answered_at, answers, ratings, checks and photo_ids, and no flag. The loop's own accDescr says only "The answers, with the score, become a FHIR record". So the first picture of the architecture a judge sees shows the one thing the entry says a model can never do.
- Fix: Relabel the edge "answers, score, follow-up answers" in docs/diagrams/loop.mmd and in the README block, then run make diagrams-render.

### K03. The judge's setup line ends with "4 high severity vulnerabilities" from a folder Dependabot does not watch
- Severity: minor
- Where: The README Quickstart setup line (README.md:544), `(cd tools/diagrams && npm ci)`; .github/dependabot.yml:1-4 and its package entries; DEPLOY.md:238
- Compared: In the same setup line, uv sync, apps/web and worker all install clean ("found 0 vulnerabilities"). I did not run the bars' setups, so this compares against the entry's own other folders.
- Evidence: In both of my fresh clones (setup.log:179, run2.log) and in CI run 36039948800 at 18:16:43Z, `cd tools/diagrams && npm ci` ends with "4 high severity vulnerabilities / To address all issues (including breaking changes), run: npm audit fix --force". Those are the last lines a judge reads before `make judge-check`, and scripts/judge_check.py never uses tools/diagrams. dependabot.yml opens with "Weekly update pull requests for every package manager in the repository", but its four entries are uv at /, npm at /apps/web, npm at /worker and github-actions; there is none for /tools/diagrams, and DEPLOY.md:238 lists the same set. The README, SECURITY.md and DEPLOY.md say nothing about it, and docs/THIRD_PARTY.md:787 says only "All dev". I ran no npm audit, so I cannot name the four packages.
- Fix: Run npm audit in tools/diagrams and update the pinned renderer or its Puppeteer chain. Add /tools/diagrams to dependabot.yml. If a high advisory has to stay, say under the Quickstart line that tools/diagrams is the dev-only diagram renderer and that judge-check does not use it. If the tests do not need it, drop it from the judge's setup line.

### K04. The Tests section says make check runs the mutation run, and its follow-up numbers come from code that has since changed
- Severity: minor
- Where: README.md:500 and :507; results/mutation.json (generated_at_utc 2026-09-24T10:51:45Z, with no commit or code hash); Makefile:34 and :253
- Compared: BlackBox's README gives each count beside the command that prints it ("make test # 32 pipeline invariants", "uv run pytest tests/ # 58 unit tests").
- Evidence: README.md:500 says "`make check` runs everything below except the browser suite and the Worker end to end". The Mutation bullet was moved under that sentence in 85be041. But the check target at Makefile:34 has no mutation, the Makefile comment at :253 says "so not in make check", and the CI log for 86e3c0c has no mutation step. The bullet says "the follow-up picker 319 of 324". core/followups.py changed after that run, at 49f835a (16:44Z, 21 lines added: the round 06 H02 rule that a flag asks only about a feature the form has). I ran `make mutation` at 86e3c0c in my clone: the gate caught 226 of 229, the follow-up picker 332 of 337, scoring 53 of 53, and the FHIR writer 1477 of 1543. So the follow-up numbers describe code that no longer exists. The score still clears the 85 percent line, and nothing ties results/mutation.json to the code it measured.
- Fix: Make README:500 say "except the browser suite, the Worker end to end and the mutation run". Run make mutation again and commit the result. Record the commit, or a hash of the four modules, in results/mutation.json, and add a test that fails when those modules have changed since the run.

### D06. Two README passages still repeat others (partly fixed)
- Severity: cosmetic
- Where: README.md:135-144 (What the AI cannot do) against :150-158 (the gate's steps) and :162-168 (Three properties that follow); README.md:332 against :160
- Compared: BlackBox also states several guarantees twice, in its failure-mode table and its "The agent cannot" table (lines 62 to 86). Second Look states the same three a third time, and its trust table adds a fourth.
- Evidence: What the AI cannot do says: the model cannot decide anything stored, cannot speak where it did not pass or on a fake table, and cannot ask more than one question. Gate steps 2, 5 and 7 say the same, and so do Three properties rows 1 to 3. test_synthetic_pass_table_never_licenses_a_flag_by_default is cited at both :141 and :167, and the fuzz test at both :139 and :166. The Architecture paragraph "The AI gate" (:332) repeats "Where it runs today" (:160): the checker is off on the live check with no flags passed, and scripts/build_walks.py runs the same gate for the walks. K01 hides the first table for now, but fixing K01 brings the triple statement back into view, and REPORT.pdf page 3 already prints 2.2 and 2.3 back to back.
- Fix: Fold What the AI cannot do under the gate's steps, or cut it to the rows the gate and Three properties do not already cover (its own words in front of a person, and risk statements). Cut the Architecture "The AI gate" lead to its first sentence.

### K05. Three small slips in the judge docs and the report
- Severity: cosmetic
- Where: docs/ACCEPTANCE.md:80; docs/REPORT.pdf page 3, from docs/report/source.md:50; docs/submission/JUDGE_QA.md:3 and Q10
- Compared: Tideline's and BlackBox's docs print the counts their commands print.
- Evidence: (1) The ACCEPTANCE row "No video file is ever committed" promises that `uv run pytest -q scripts/tests/test_no_video_files.py` prints "2 passed". The file has 4 tests (lines 37, 41, 52 and 62), and because pyproject's addopts already holds -q, the command prints only "...." with no count line. The same page says a row that does not print what it says is a promise not kept. (2) On REPORT.pdf page 3, "Where it runs today ... so 0 of the 3 walks shows a checker question" is followed straight away by "In the build measured here, 0 of the 3 walks carries a checker question". (3) JUDGE_QA Q10 says "The real run of Sep 24", while the README's real and synthetic table, Known weaknesses and the report say Sep 23, Pacific time (Sep 24 UTC). JUDGE_QA's first line still says "checked against this branch on 2026-09-23", above a Q19 about Sep 24.
- Fix: (1) Make the row say "4 passed" and run the command without the extra -q, or say it prints four dots. (2) Drop the paragraph at docs/report/source.md:50, since the README section now says the same thing, and run make report-pdf. (3) Write "Sep 23, Pacific time" in Q10, and date the page's check line Sep 24.

## Checked by independent skeptics

Each finding above cosmetic went to one skeptic subagent, told to refute it at 86e3c0c.

- K01: confirmed, major.
- K02: confirmed, minor.
- K03: confirmed, minor.
- K04: confirmed, minor.
