# Critic round 05

Highest severity: minor
Commit: 7688115

A critic subagent that wrote none of the code wrote this round on 2026-09-24 UTC, reading the repo at
7688115 read-only, the live site (the same code) with GET requests only, and Alex's two public
repositories as the bar. Its report follows as it came back.

First I read CRITIC_01 to CRITIC_04 and the docs/DECISIONS.md lines dated 2026-09-24, and diffed d870842 against 7688115. I cloned 7688115 into my scratch folder with pushing turned off and ran the README Quickstart word for word, with Playwright's browsers going into an empty folder. Setup took 36 s. Then `make judge-check` printed "judge-check: 6 of 6 steps passed, offline, with no key", with "python: 2009 passed, 2 skipped, 9 xfailed" (2020 tests). Its step timers add up to 248 s. After that `scripts/verify_claims.py` checked 111 README claims, 40 alt texts and 9 Devpost claims, and all of them match. All 189 relative links in the README resolve. I shallow-cloned Tideline and BlackBox and counted each README's words the same way for all three, leaving out Mermaid blocks, comments and folded `<details>` blocks. On the live site I used Playwright at 390 px with GET requests only, and aborted every other request, which means only the site's own HEAD pings. No request went to either forbidden host. I opened 22 routes and drove all three walks through to the record, View as FHIR and the city view. I pulled out the v02 Bundle, fetched both /how-we-know frames, and rendered all 8 pages of REPORT.pdf with PyMuPDF. With gh I read CI, issue #4, the pull requests and branches, and hl7-eu/oah PR 5 and issues 6 to 9. I checked every finding a second time against the code or the live page before keeping it.

## Round 04, checked again
- F01: fixed. Live /walk/v02 now ends on "Your answers": every answer with "Not tested on this phone" or "Not a tested feature" beside it, and "A volunteer who kept a score from the test carries it with every answer, as the example record shows", which links to /two. The new label causes a new problem, reported as G02.
- F02: fixed. Live /how-we-know shows /photos/v02-00127.jpg and v02-00143.jpg (both 200) with alt text above their cards. It also shows "Claude Sonnet 5 passed this feature too, and said no on this frame in all 3 of its runs", the same line for Opus 5.5, "Nobody has labelled this frame", and display names for the models.
- F03: fixed. JUDGE_QA.md:91 now says CI "was red at times from Sep 21 to Sep 24 ... `main` has been green since fb3ff24". gh shows every main run since fb3ff24 as green, 7688115 included.
- F04: fixed, apart from one slip the fix brought in (G03). /judges opens with `judges.intro` (page.tsx:52), /about with `about.lead`, README.md:570 and :586 are reworded, the plant sentence moved to the middle column, /how-we-know uses display names, and the walk's city view says "Dams, weirs and other barriers".
- D05: fixed. README.md:571 adds "It is empty until the first real check; `make demo-offline` shows it full." The scorecard's Technical row cites `fhir/sandbox_ledger.jsonl` and `docs/notes/sandbox_library.md`, and its Thin line names hl7-eu/oah issue 8.
- D06: partly. Two diagrams now fold and two long bullets were cut, but the README grew from 628 to 638 lines. Reported again below.
- D07: partly. The issue body, rewritten at 2026-09-24T14:14Z, now gives four models, 9 of 16, 35 of 64 and 41.11 USD uncapped, and the `person_no_swallow` step is gone. Two counts are still off. Reported again below.
- E02: fixed. ARCHITECTURE.md:13 and :133-135 and ADR 0005:23-24 now say that sample records from both emitters are validated in CI and that golden vectors hold the live emitter to them. CI's `make check` runs `fhir-validate` with Java 17.
- E06: fixed. REPORT.pdf page 1 now has the subtitle "A two-minute test of how well a volunteer sees a creek, and a model that may only ask" on a single line.

## Where Second Look already meets or beats the bar
- A fresh clone, the Quickstart, then `make judge-check` gave 6 of 6 PASS offline with no key, including "28603 values in 26 files regraded from raw replies and seeds ... every one matches". BlackBox's judge path regrades no model output.
- The claims hold. verify_claims matched 111 README claims, 40 alt texts and 9 Devpost claims against results/, and all 189 relative README links resolve.
- /how-we-know now shows the evidence at the claim: the frame, the model's words, the gate's words, the other passing models' "no", and the fact that nobody has labelled the frame. BlackBox puts its root cause screenshot at the top of its README. Neither bar has a live evidence page.
- The walk now ends on its own result. It lists 23 answers with a score column and has View as FHIR: 18 Observations, a QuestionnaireResponse and a Provenance. Its city view names "Dams, weirs and other barriers" and "Pipes and drain outlets", each with its Policy Brief source. All of this runs in a browser with nothing to install, while BlackBox's live demo needs Docker, DataHub and a key.
- The live pages state their limits in place. /two says "Example record, made by hand for this demo.", /city says "0 visits at 0 spots", /demo gives the lock in UTC and PDT, and each walk says "never stored, never counted and never sent".
- /verify checks the audit chain again in the browser and shows "In Bitcoin block 968372". Neither bar has anything like it.
- CI is green on 7688115 on main and on depth. hl7-eu/oah PR 5 and issues 6 to 8 are open, and a third party opened PR 9 from issue 6.
- All 22 routes I opened fit 390 px with no sideways scroll, and the landing page loads in 0.6 s.
- The report's title block now fits whole, as both bars' title blocks do.

## Findings
### G01. One of the four tested features is never asked in the creek check, so the measure the README names for it can never appear
- Severity: minor
- Where: content/form.yaml (no item has `feature: dug_out_channel`); content/features.yaml:30 ("the app has no matching item"); core/act.py:38-43 and :139-145; content/followups.yaml (`low_score` needs_items); README.md:429; docs/devpost.md:114.
- Compared: Tideline says plainly where something is missing: "Stations without a sensor for a product (SF has no thermometer!) get a friendly empty state" (README:34). BlackBox's safety table ties each claim to the code path that makes it happen.
- Evidence: Across the 23 form items the feature tags are artificial_bank 1, pipe_running 2, invasive_plant 2 and null 19. No item is tagged dug_out_channel. Findings come only from answers mapped through the form, so `dug_out_channel -> city_reconnect_floodplain` can never fire. The `low_score` photo prompt and `rating_check` cannot reach it either. On my live v02 walk the rows marked "Not tested on this phone" were Bank type, the two pipe questions and the two plant questions, and no row was about a dug-out channel. Invasive plants reach no city measure either, by design (act.py:37). So when I answered Yes to plants, the city view listed only barriers and pipes. Yet README.md:429 lists the city actions as including "reconnect the floodplain", and docs/devpost.md:114 says the four features "are the ones that tell a city what a creek needs". The only place a dug-out channel can come up is the checker's follow-up, which is off on the live site. Even there it would ask a person to look again at something the check never asked them. No public doc says the check has no dug-out question.
- Fix: Add one sentence to README How OneAquaHealth is used and to Known weaknesses: "The official app has no question for a dug-out channel, so the check asks none: that score is kept but stands beside no answer, 'reconnect the floodplain' waits for one, and plants have no measure of their own." Change devpost.md:114 to say that built banks and pipes tell a city what a creek needs.

### G02. The walk record tells a judge who just took the test that they were "Not tested on this phone"
- Severity: minor
- Where: apps/web/components/WalkFlow.tsx:180; content/locales/en.json:569; worker/src/core/walks.ts:44 (`scores: []`); README.md:551.
- Compared: BlackBox's resolved screen shows the result of the run the viewer started (docs/screenshots/04-resolved.png: the before and after KPI and the real diff).
- Evidence: Every tested feature on the walk record gets "Not tested on this phone", whatever the phone holds, because the walk's observer always has `scores: []` and the label is fixed. Both the README path ("the test (about four minutes with its lesson), a creek from your desk, a record made on your phone") and /judges send a judge to the test first. The test's end offers "Keep my score for creek visits ... Use it on a creek visit so your score travels with your observation", and the token goes to `sl_contributor_token` on the phone. A judge who follows the path is then told they were not tested on this phone, right above "A volunteer who kept a score from the test carries it with every answer". I did not take the test myself because it POSTs, so this comes from the code.
- Fix: Change that one locale string to what is true for everyone, for example "No score in a demo record".

### D06. The README is still well over twice the bar's length (partly fixed)
- Severity: minor
- Where: README.md, 638 lines. For judges is at line 549 and See it work at 575, both 10 lines further down than at round 04.
- Compared: BlackBox's README is 297 lines, with See it work at line 38. Tideline's is 260 lines.
- Evidence: Counting words outside Mermaid, comments and folded blocks gives 6,812 (6,953 at d870842), against 2,485 for BlackBox and 2,861 for Tideline counted the same way. The folded blocks went from 5 to 7. The largest sections are How OneAquaHealth is used (944 words), Architecture (888), For judges (806), Why trust (787) and Numbers at a glance (628).
- Fix: None of these touches the AI table's cost rows, Three properties or the section order. Fold the 12-row surface table in How OneAquaHealth is used into `<details>` under its opening paragraph. Cut the iNaturalist cell to one sentence and a link to ADR 0011. Fold "What was built, screen by screen", since it repeats /judges. Cut Security and privacy to two lines pointing at SECURITY.md and DATA_HANDLING.md. Cut the 164-word judge-check paragraph in the Quickstart to two sentences above the pasted block.

### D07. The status issue still gives two stale counts (partly fixed)
- Severity: cosmetic
- Where: GitHub issue #4 body, edited 2026-09-24T14:14:43Z, public from Sep 30.
- Compared: BlackBox's only open PR is its receipt, and that PR's body is built only from recorded evidence.
- Evidence: "What is green" says "104 Playwright tests", but results/test_counts.json (measured at ca7dc10) and README.md:486 say 107. "What is live" says "/judges with 14 doors", but live /judges has 15, and the DOORS list has 15 entries at both d870842 and 7688115.
- Fix: Change 104 to 107 and 14 to 15, or drop both counts.

### G03. Three small slips
- Severity: cosmetic
- Where: apps/web/lib/answers.ts:55-58 with apps/web/components/FormQuestion.tsx:125; README.md:444; apps/web/app/about/page.tsx:20-22.
- Compared: Tideline's empty states say what is missing ("a friendly empty state, not an error"), and its words match what the reader sees.
- Evidence: (1) On live /walk/v02, pressing Next on "Habitats", "Natural debris" and "Which ones?" with nothing ticked stores an empty list. The record then lists those three questions with nothing under them, because `answerRows` skips only undefined answers. "Which ones?" offers only "Not sure" while the plant lists wait on Rachel's check. (2) README.md:444 reads "credited by author and licence on `/credits` The Bay Area plant list waits on a check". The full stop was lost when the sentence moved. (3) /about now opens with no duration, which was the F04 fix, but it still ends with the button "Find out in two minutes" (`landing.cta`). deviations.md:36 logs that string for the landing page only.
- Fix: (1) Skip an empty list in `answerRows`, or make Next with nothing ticked act as "None of these". (2) Add the full stop. (3) Give the /about button its own string, such as "Take the test", or name /about in deviations.md:36.
