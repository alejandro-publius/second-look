# Critic round 03

Highest severity: major
Commit: 6f40364

A critic subagent that wrote none of the code wrote this round on 2026-09-24 UTC, reading the repo at
6f40364 read-only, the live site (the same code) with GET requests only, and Alex's two public
repositories as the bar. Its report follows as it came back.

I read CRITIC_01, CRITIC_02 and DECISIONS.md, which records the choices kept on purpose on 2026-09-24. I checked each round 02 finding at 6f40364 with greps, diffs and gh. I cloned 6f40364 into my scratch folder. Pointing PLAYWRIGHT_BROWSERS_PATH at an empty folder, I ran the README Quickstart word for word (37 s), then `make judge-check` (263 s, "judge-check: 6 of 6 steps passed, offline, with no key"), then `scripts/verify_claims.py`. I also checked all 208 README links and image paths, and 107 `path::test` citations across 10 docs a judge opens. I shallow-cloned Tideline and BlackBox and read both READMEs, BlackBox's CI and its examples/sample-incident/. On the live site I used GET-only Playwright at 390 px with every non-GET request aborted, including the site's own HEAD pings to / and /about. No request went to either forbidden host. I opened 21 routes, drove /walk/v02 and /walk/v03 to their record and city view, and played the v02 clip in WebKit and Chromium. I compared the committed screens, GIF frames and REPORT.pdf page 1 with the live pages. With gh I read the GitHub state: CI, branches, issue #4, and upstream hl7-eu/oah PR 5 and issues 6 to 8. I checked every finding a second time before keeping it.

## Round 02, checked again
- D01: fixed. docs/REAL_VS_SYNTHETIC.md:15 now reads "real, from the paid sweep of Sep 23, Pacific time", which matches `"real": true` in results/model_pass_table.json. Line 60 now says "the four models".
- D02: fixed. The 31 screens and the GIF were captured again from the live site at 9edd30a: walk-city.webp reads "Pipes and drain outlets / Checks that saw it: 1"; consent.webp and GIF frame 1 name "the kind of link you came from"; demo.webp gives one moment, in UTC and PDT.
- D03: fixed. Live /judges has 14 doors, each with one line and a time. They include the README, REPORT.pdf, the model card, the footage example and the code, all marked "Opens on Sep 30". /about links /judges. /how-we-know shows the pass table and "The gate dropped 29 of them and kept 35". Its file names are still plain text, not links.
- D04: partly. examples/footage-flag/ now traces one kept flag and one dropped flag from the committed answer to the question. The live site still shows no checker question, and no gallery screen shows one. The walk the /judges doors open ends with "The checker asked nothing" (E04).
- D05: partly. devpost.md:100, README.md:518 and the /judges "For a city" door now go to the walk's city view and say the live creek stays empty. But docs/JUDGE_SCORECARD.md:13-15 still points Impact at `/spot` and `/city?creek=strawberry-creek`, both empty live, and README.md:537-538 still lists their full content.
- D06: partly. The README now shows five screens and moved 26 to docs/screens/README.md. It is still 605 lines and 73,700 bytes, with See it work at line 542.
- D07: still true, kept on purpose (DECISIONS.md:99). What is new: issue #4 and docs/SUBMISSION_CHECKLIST.md now say things that are untrue (reported below).
- D08: fixed. PLAN.md:165 now says a paid panel may add sessions; deviations.md:35 states the Prolific funding (up to 80 finished sessions), that Prolific pays the participants, and the ethics position; README.md:568 says the panel study has had no ethics review.
- D09: fixed. docs/notes/sandbox_library.md:3-8 now says the read-back is word for word from Sep 21, what the corrected Library says, and that the update waits on issue 8. The golden Library says "1 visit record".
- D10: still true. README.md:500 describes the six steps but does not paste them. My run printed six PASS lines, ending "judge-check: 6 of 6 steps passed, offline, with no key".
- D11: partly. /judges ("Take the test, about four minutes with its lesson"), /poster and README.md:21 are fixed, and the frozen landing line is logged (deviations.md:36). Three places still say two minutes: README.md:434 ("train and test the volunteers in two minutes"), VOICE_SCRIPT beat 4 ("that test, in two minutes") and JUDGE_SCORECARD.md:21 ("doing it in two minutes").
- D12: fixed. SECURITY.md:4 now says "which the privacy page points to", and line 33 makes an exception for the spot name.
- D13: fixed. devpost.md:81 now says the pipeline "ran on 46 frames ... there the gate dropped 29 of 64 candidate flags", with claim markers.
- D14: fixed. README.md:529 links docs/video/SHOTLIST.md and VOICE_SCRIPT.md.
- D15: fixed. README.md:492 says "Needs git, uv (it fetches Python 3.12) and Node 20 or later with npm."
- D16: fixed. results/test_counts.json was measured on a clean tree at 5facc07 and gives 2014 Python tests. My judge-check at 6f40364 ran 2003 passed, 2 skipped and 9 xfailed, which is 2014. ACCEPTANCE row 18 reads its 13 from the file.
- D17: partly. The stale depth comment is gone and the steps have names, but CI is still one job, `check`.
- D18: fixed. README.md:544 says "above"; `fhir` is unlinked and the self-link is gone; ARCHITECTURE.md:3 says "four diagrams"; JUDGE_QA Q18 says "reads the last HL7 validator run". New slips of the same kind are listed under E06.

## Where Second Look already meets or beats the bar
- A fresh clone, then the README Quickstart from an empty browser folder, then `make judge-check`: 6 of 6 passed in 263 s. It prints "python: 2003 passed, 2 skipped, 9 xfailed", "worker: pass 15" and "28603 values in 26 files regraded". BlackBox's judge-check regrades no model output.
- examples/footage-flag/ is written by a script and held by `make check`. For one kept flag and one dropped flag it gives the committed answer line, the gate's reason in its own words, and the follow-up question. It also shows every model's answers on the same frame, including the two passing models that said no. This matches BlackBox's examples/sample-incident/.
- /judges is a live page with 14 doors, each saying what it shows and how long it takes, and /about links to it. Neither bar has a live judges page (Tideline has no public instance).
- /how-we-know renders the pass table and the gate's 29 of 64 from results/ at build time.
- The README's 208 links and image paths all resolve. The 107 `path::test` citations in 10 judge docs are all real. verify_claims: "104 claim(s), 39 alt text(s) checked, all match results/".
- Live: 21 routes each answered 200 with their own title, none wider than 390 px. The v02 walk runs to its record, and its city view counts pipes once.
- The stated limits sit on the pages themselves: /two: "Example record, made by hand for this demo."; /city: "0 visits at 0 spots"; the walk's FHIR view: "This one was made on your phone and was not checked."; the consent: "about four minutes".
- /verify checks the audit chain again in the browser and shows each line "In Bitcoin block 968372". Neither bar has anything like it.
- CI is green on 6f40364, on both main and depth.
- Contributed back: hl7-eu/oah PR 5 and issues 6 to 8 are open, and a third party has already opened a fix (their PR 9) from issue 6. BlackBox has two upstream PRs.

## Findings
### E01. The health card, the entry's human and animal health answer, is visible nowhere a judge can open
- Severity: major
- Where: apps/web/components/SpotRecord.tsx:216-231, the only place the card renders; docs/devpost.md:50 and :116; README.md:438; docs/JUDGE_SCORECARD.md:15; docs/video/SHOTLIST.md:49 (12.3) and VOICE_SCRIPT beat 12.
- Compared: BlackBox puts a screenshot of each capability it claims in its README, captioned with its result ("verified repair (32/32, real diff, git branch)", the incident it raised in DataHub).
- Evidence: The Devpost field "Users and impact on ecosystem and human health" says: "the health card gives one action for the person, one for the pet and one for the city". The card renders only on /spot with a stored record. Live /spot says "This link names no spot.", and /spot?id=example says "No record for this spot." That much follows from the known limit. But nothing stands in for it: none of the 31 gallery screens shows the card; spot-record.webp (mock) ends at the visits, above the FHIR view and the card; the walk record and /city?walk=v02 have no card, and CityView.tsx has no health string; SHOTLIST 12.3 says "Back to `/city`, on the health card line", a line /city does not have, so beat 12 would say "the health card gives one action for you, one for your dog" over a page without it.
- Fix: Capture one (mock) screen of /spot?id=example scrolled to "What you can do". Add it to docs/screens and to the Devpost gallery, and cite it from both Devpost fields and scorecard row 15. Point SHOTLIST 12.3 at that screen, not /city.

### D04. The live site still shows no checker question (partly fixed)
- Severity: minor
- Where: docs/screens/ and results/screens.json; apps/web/app/judges/page.tsx:18.
- Compared: BlackBox shows its agent at work at the top of its README (02-investigation.png, 03-rootcause.png).
- Evidence: examples/footage-flag/README.md is good, but it opens on Sep 30 and it is text. No screen shows the "Look again?" question with its "the checker noticed" note. The walk the /judges doors open (content.walks[0], v02) ends with "The checker asked nothing".
- Fix: Capture one (mock) screen of WalkFlow's question stage with the kept flag from the example, and link it from the example and from /how-we-know.

### D05. The scorecard still sends Impact to empty live pages
- Severity: minor
- Where: docs/JUDGE_SCORECARD.md:13-15; README.md:537-538.
- Compared: every "where to look" in BlackBox's scorecard opens something that shows the claim (PR #1, examples/sample-incident/).
- Evidence: Row 13 cites `/spot`, row 14 `/city?creek=strawberry-creek`, and row 15 "the health card on `/spot`". Live, those pages read "This link names no spot." and "0 visits at 0 spots ... No measure applies to what people have reported here so far." The README's own judge path and /judges now avoid both pages.
- Fix: Point the rows at `/two` (an answer beside "4 of 4 on this feature"), `/walk/v02` then "See this creek as a city would", and the mock spot screens. Add "(needs a stored record; see the mock screens)" to README.md:537-538.

### D06. The README is still twice the bar's length, and See it work is near the end (partly fixed)
- Severity: minor
- Where: README.md, 605 lines. For judges is at line 516 and See it work at 542.
- Compared: BlackBox's README is 297 lines, with See it work at line 38. Tideline's is 260 lines.
- Evidence: the gallery fix landed. But Architecture, Tech stack, API and MCP (lines 163 to 401) still stand between the AI tables and "How OneAquaHealth is used", which serves Impact (30%).
- Fix: Move For judges and See it work up under Numbers at a glance. Fold Tech stack, API and MCP tools into `<details>`.

### D07. The kept status issue and submission checklist now say untrue things
- Severity: minor
- Where: GitHub issue #4, public from Sep 30; docs/SUBMISSION_CHECKLIST.md:16, :18, :22 and :27.
- Compared: BlackBox's only open PR is its receipt, and its scorecard dates each change.
- Evidence: Issue #4 (updated 2026-09-24T10:22Z) says: "three models ... 6 of 12 model and feature pairs passed ... the gate kept 33 of 63 candidate flags. Spent within the 40 dollar cap". It also asks Alex to read `person_no_swallow`, which "carries your name as approver"; that sentence was dropped (DECISIONS.md:78). The README now says four models, 9 of 16 passed and 35 kept of 64. The model card says 41.1 USD in all, and DECISIONS.md:81 says the calls were not capped. The checklist says verify_claims "fails while results are synthetic" and lists it under "Expected failures"; my run passed it. It says demo_url is "skipped until deployed". It says to record the video to the superseded docs/video_script.md.
- Fix: Rewrite issue #4's "What is live" to today's numbers and drop step 2. Mark verify_claims and demo_url as passing in the checklist, and point its video line at docs/video/SHOTLIST.md.

### D10. The README still does not show judge-check's output
- Severity: minor
- Where: README.md:500
- Compared: BlackBox pastes its five-line "BLACKBOX JUDGE CHECK" block.
- Evidence: the README says "six steps, each printed with ok or FAIL". My run printed six PASS lines, starting "PASS  tests ... python: 2003 passed, 2 skipped, 9 xfailed", and took 263 s.
- Fix: Paste the six PASS lines and the last line under the Quickstart, with the counts as claim markers from results/test_counts.json.

### D11. "Two minutes" outside the frozen strings (partly fixed)
- Severity: minor
- Where: README.md:434; docs/JUDGE_SCORECARD.md:21; docs/video/VOICE_SCRIPT.md:16 (beat 4); docs/deviations.md:36.
- Compared: BlackBox gives its run one duration (about 180 s) everywhere.
- Evidence: README.md:434 says "train and test the volunteers in two minutes", while the consent says "It takes about four minutes." and /about says "a two-minute lesson and a sixteen-photo test". deviations.md:36 says "the README say[s] about four minutes with the lesson".
- Fix: Say "about four minutes" in README.md:434, scorecard line 21 and beat 4. Those strings are not frozen.

### E02. "Every record validates" and "every emitted resource is validated in CI" claim more than CI checks
- Severity: minor
- Where: README.md:120 and :413; docs/devpost.md:50 and :77; docs/submission/JUDGE_QA.md:26.
- Compared: BlackBox states the limits of its demo in the README itself: "treat the incident realism as illustrative and the machinery as the contribution".
- Evidence: The Devpost says "Every record validates against their implementation guide at commit b907cf0 with zero errors." results/fhir_validation.json has `files_validated: 14`, a fixed list of golden and sample files, two of them from one walk (v03). deviations.md:31 says the validator "checks a fixed list of files and never saw a record made on a phone". The live walk says "This one was made on your phone and was not checked." Stored production records never pass through the validator.
- Fix: Say "sample records from both emitters (14 files, 2 of them walk records) validate with 0 errors in CI, and golden vectors hold the live emitter to them" in all five places.

### E03. The plant lists the docs describe are empty and unapproved
- Severity: minor
- Where: README.md:419 and :375; docs/submission/JUDGE_QA.md:20-21; docs/JUDGE_SCORECARD.md:71; content/regions/california-bay-area.yaml:6-8.
- Compared: BlackBox reports its weak ablation result instead of claiming more ("the ablated agent can still brute-force a correct diagnosis ... We report that").
- Evidence: The README's iNaturalist row describes "research grade sightings of the region's listed invasive plants". JUDGE_QA Q4 answers "The Bay Area list from the Cal-IPC Inventory", with the proof `content/regions/california-bay-area.yaml`. That file reads `approved: false`, `invasive_plants: []`, `source: "Cal-IPC inventory (to be checked by Rachel)"`. The scorecard offers "a second plant list" in heraklion.yaml, which has `invasive_plants: []` and `creeks: []`. ADR 0011:58-59 says the job "asks nothing and every creek says there are no recent sightings on record". The README does not say so. The check's which-plant question falls back to "No plant list for this region yet. Pick Can't tell." (en.json:140, FormQuestion.tsx:111).
- Fix: Get Rachel's approval (ALEX_TODO item 6). Until then, add "the Bay Area list waits on a check; until then the line reports no sightings" to README.md:419 and Q4. Say "a second city scaffold, its lists still to fill" in the scorecard.

### E04. The walk the judges open says the checker asked nothing, for a reason that did not apply
- Severity: minor
- Where: content/locales/en.json:537 (`walk.checker_none`); apps/web/app/judges/page.tsx:18; content/walks.yaml (v02).
- Compared: BlackBox's run table gives the numbers behind each outcome (distractor rejected, "max effect ~1.27x").
- Evidence: Live /walk/v02 ends: "The checker asked nothing. It is only allowed to ask about a feature it passed the same test on, and 0 of its guesses on this clip were stopped for that reason." v02's build record is `kept: {}, dropped: 0`, so no model proposed any flag and the pass rule stopped nothing. Live /walk/v03 shows the gate at work instead: "1 of its guesses on this clip were stopped". It also has a number slip.
- Fix: When `dropped` is 0, say "No model saw any of the four features in this clip, so the checker had nothing to ask", and fix "1 ... were". Point the /judges record door at v03, or link the line to /how-we-know.

### E05. The /two door promises a comparison the page cannot show today
- Severity: minor
- Where: content/locales/en.json:440; live /two.
- Compared: BlackBox's receipt, PR #1, is there when a judge opens it and shows what the README says.
- Evidence: The door reads "Shows that a volunteer answer fits the same record shape as a lab result". Live /two, titled "Two kinds of observer", shows one card and says "Their sandbox did not answer, so only our record is shown." The README and the Devpost state the outage. The door does not.
- Fix: While `theirs_status` is down, show the committed EXAMPLE lab result (fhir/golden/example-lab-result-strawberry-creek-1.json) as the second card, labelled example. Or add "while their sandbox is down, ours shows alone" to the door.

### D17. CI is still one job
- Severity: cosmetic
- Where: .github/workflows/check.yml:7
- Compared: BlackBox's ci.yml has five jobs (backend-tests, lint, pipeline-invariants, frontend, secrets-scan).
- Evidence: there is one job, `check`, with named steps: make check, make reproduce, make e2e and the Worker e2e.
- Fix: Split it into python, reproduce, web-e2e and worker-e2e jobs.

### E06. New small wording slips
- Severity: cosmetic
- Where: README.md:518, :359 and :553; docs/ACCEPTANCE.md:6; content/locales/en.json:448; /city?walk=v02; docs/REPORT.pdf page 1; docs/REAL_VS_SYNTHETIC.md:3-4 and :28.
- Compared: Tideline prints "98 tests" beside the command that prints them, and its claims match what runs.
- Evidence: README.md:518 promises "the full 24 question check", but the walk shows "Question 1 of 23". README.md:359 says "The same three as images" after four diagrams, and leaves out loop.svg. ACCEPTANCE.md:6 says judge-check "runs the first five rows", but row 3 (the validator) is not run, as its own row 15 says. The /judges footage door says "from the raw reply", but the example says its line is the answer after `force_answer`, "not the reply exactly as the model sent it". The walk's city view shows "barriers?. OneAquaHealth Policy Brief". The report's subtitle leaves "ask" alone on its second line. REAL_VS_SYNTHETIC.md:3-4 cites "Update 10 tier 3 item 10", and its row 28 has three cells in a four-column table. README.md:553 cites city.webp, the empty live creek, for "What the city then saw".
- Fix: README.md:518: "23 question". README.md:359: "The same four", and add loop.svg. ACCEPTANCE.md:6: "runs rows 1, 2 and 5, and reads row 3's last run". /judges: "from the model's committed answer". Drop the "." after a question. Rebreak the report subtitle. REAL_VS_SYNTHETIC.md: drop the update reference and fill the cell. README.md:553: cite walk-city.webp.
