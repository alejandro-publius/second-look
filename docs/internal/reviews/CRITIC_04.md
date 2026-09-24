# Critic round 04

Highest severity: minor
Commit: d870842

A critic subagent that wrote none of the code wrote this round on 2026-09-24 UTC, reading the repo at
d870842 read-only, the live site (the same code) with GET requests only, and Alex's two public
repositories as the bar. Its report follows as it came back.

I read CRITIC_01 to CRITIC_03 and the lines of docs/DECISIONS.md dated 2026-09-24, then checked each round 03 finding at d870842 with greps, the rendered pages and gh. I cloned d870842 into my scratch folder with pushing disabled and ran the Quickstart word for word, with Playwright's browsers going into an empty folder. Setup took 34 s on warm caches. `make judge-check` then took 255 s and printed "judge-check: 6 of 6 steps passed, offline, with no key". After that I ran `scripts/verify_claims.py` on the README and on the Devpost text. I also ran `make demo-offline` on two spare ports and opened its /city and /spot. I checked 188 relative README links, and 107 `path::test` citations and 496 backticked paths across 15 docs a judge opens. I shallow-cloned Tideline and BlackBox and compared their READMEs (lines, rendered words, where See it work and For judges sit), BlackBox's scorecard and screenshots, and Tideline's test lines. On the live site I used GET-only Playwright at 390 px and aborted every non-GET request, including the site's own HEAD pings. No request went to either forbidden host. I opened 25 routes and drove /walk/v02 and /walk/v03 through the record, View as FHIR and the city view, and I pulled out the Bundle a walk makes. I rendered all 8 pages of REPORT.pdf. With gh I read the CI runs, issue #4, the open pull requests and branches, and upstream hl7-eu/oah PR 5 and issues 6 to 9. I checked every finding a second time before keeping it.

## Round 03, checked again
- E01: fixed. docs/screens/spot-health.webp shows "What you can do" with You, Your pet, The city and the three sources. It is Devpost gallery item 4 (devpost.md:173), scorecard row 15 cites it, and SHOTLIST 12.3 now points at /spot?id=example ("`/city` has no health card").
- E02: partly. README.md:120 and :428, devpost.md:50 and :77, and JUDGE_QA Q5 now say "sample records from both emitters". ARCHITECTURE.md:13 and :133 and ADR 0005:23 still say every visit or every emitted resource validates. Reported below.
- E03: fixed. README.md:378 and :434 and JUDGE_QA Q4 say the list waits on Rachel's check and the line reports no sightings. The scorecard says "A second city scaffold, its lists still to fill".
- E04: fixed. Live /walk/v02 ends "No model saw any of the four features in this clip, so the checker had nothing to ask." /walk/v03 ends "1 of its guesses on this clip was stopped for that reason."
- E05: fixed. The live /two door reads "While the OneAquaHealth sandbox is down, our record shows alone."
- E06: partly. The 23 question slip, "The same four" with loop.svg, ACCEPTANCE.md:6, the footage door, the stop after the city question, REAL_VS_SYNTHETIC and README.md:576's screen are all fixed. REPORT.pdf page 1 still leaves "ask" alone on the subtitle's second line. Reported below.
- D04: fixed. Live /how-we-know now shows "One flag kept, one dropped" with "A person at the creek would then be asked this: The checker noticed something that may be a channel that was deepened or straightened. Want to look again?" and the gate's words for the dropped flag. It shows no frame (F02).
- D05: partly. Scorecard rows 13 to 15 now open /two, /walk/v02 then the city view, and spot-health.webp. README.md:561 still lists the full content of the empty live /city page. The scorecard's Technical row cites `/two` for the sandbox mirror. Reported below.
- D06: still true, and longer. It is now 628 lines (605 at round 03) and about 8,000 rendered words, with For judges at line 539 and See it work at 565. Reported below.
- D07: partly. SUBMISSION_CHECKLIST now marks demo_url and verify_claims as pass and names SHOTLIST for the video. Issue #4 is unchanged since 2026-09-24T10:22Z and still says untrue things. Reported below.
- D10: fixed. README.md:515-523 pastes the six steps and the last line from results/judge_check.json. My run printed the same six PASS lines, with "python: 2009 passed, 2 skipped, 9 xfailed". That is 2020, as results/test_counts.json says; the extra skip was "gh not logged in" in my clone.
- D11: fixed. README.md:449, the scorecard's Innovation line and beat 4 now say "about four minutes". The first line of /judges is noted under F04.
- D17: still true (one job, `check`, .github/workflows/check.yml:7). It is a stated limit, so it is not counted.

## Where Second Look already meets or beats the bar
- In a fresh clone, the Quickstart then `make judge-check` gave 6 of 6 PASS in 255 s, offline, with no key. It printed "reproduce: 28603 values in 26 files regraded from raw replies and seeds ... every one matches". BlackBox's judge-check regrades no model output.
- The README's pasted judge-check block is made of claim markers read from results/judge_check.json, so it cannot drift from the recorded run. BlackBox pastes a fixed block.
- Live /how-we-know shows the pass table, "The gate dropped 29 of them and kept 35", and a kept and a dropped flag with the question and the gate's own words, read from examples/footage-flag/example.json at build time. Neither bar has a live evidence page.
- `make demo-offline` worked from the clone with no network. Its /spot lists each answer beside "4 of 4 on Built banks, tested Sep 25" or "Not a tested feature". Its /city shows the measures, "Faculty Glade bridge, 2 people, after 7 dry days" with "Referral as FHIR", and the downstream notes by reach. BlackBox's full demo needs Docker, DataHub and a key.
- The claims hold. verify_claims checked 120 claims and 40 alt texts in the README and 9 claims in the Devpost text, and all match. All 188 README links, 107 `path::test` citations and 496 backticked paths exist.
- The live pages state their limits in place. /two says "Example record, made by hand for this demo." The walk's FHIR says "This one was made on your phone and was not checked." /how-we-know says "not something a volunteer saw", and /demo gives the lock time in UTC and PDT.
- /verify checks the audit chain again in the browser and shows each line "In Bitcoin block 968372". Neither bar has anything like it.
- CI is green on d870842 on main and depth. hl7-eu/oah PR 5 and issues 6 to 8 are open, and a third party opened PR 9 from issue 6.
- 25 live routes answered 200, and none is wider than 390 px.

## Findings
### F01. The one record a judge can make shows no answer and no observer score
- Severity: minor
- Where: apps/web/components/WalkFlow.tsx:158-177 (the record stage); content/locales/en.json:546 (`walk.done_body`); the /judges door "A sample record" (apps/web/app/judges/page.tsx:34); live /walk/v02.
- Compared: BlackBox ends its run on a screen that shows the outcome itself: the before and after KPI and the real diff (docs/screenshots/04-resolved.png, captioned "verified repair (32/32, real diff, git branch)").
- Evidence: A judge watches the 40 second clip and answers 23 questions. The live record page then reads only: "Your record from the clip / Here is the record your answers made, in the same shape a real visit takes. ... / Every link inside the record checks out / The checker asked nothing. ... / View as FHIR / See this creek as a city would / Try another creek". No answer is listed and no score is shown. The Bundle behind View as FHIR holds 18 Observations and one QuestionnaireResponse, the creek check. Its Practitioner has no qualification and there is no test-sitting QuestionnaireResponse, so this record carries no score. The live site shows the score line only on /two, on a hand-made example. The view that makes the point already exists: the local /spot in `make demo-offline`.
- Fix: On the walk's record screen, show the answers with the rows /spot already uses, put "not tested on this phone" in the score column, and add one line saying that a volunteer who kept a score carries it here, with a link to /two.

### D06. The README is almost three times the bar's length, and it grew again
- Severity: minor
- Where: README.md, 628 lines and 76,256 bytes. For judges is at line 539 and See it work at 565.
- Compared: BlackBox's README is 297 lines and 2,822 rendered words, with See it work at line 38. Tideline's is 260 lines and 3,094 words.
- Evidence: Mine counts about 8,000 rendered words, leaving out the claim markers and the Mermaid blocks. The largest sections are Why trust 840 words, the AI table 604, How OneAquaHealth is used 510, See it work 484, Known weaknesses 432 and The gate 426. Three diagrams still render in full. The gate is told four times: Why trust, What the AI cannot do, the seven steps, and the sequence diagram with Three properties. `make reproduce` is described twice, at :468 (152 words) and :515 (164 words).
- Fix: Keep the order the brief sets and cut inside it: fold the FHIR graph and the AI gate sequence diagram into `<details>`, as the system map already is; merge Three properties that follow into What the AI cannot do; move the mutation row and the two cost rows out of the AI table into Tests and the model card; cut the Evals reproduce bullet (:468) to one line that points at the Quickstart; cut Known weaknesses bullet 2 (:585, the simulation) to one sentence and its file.

### F02. /how-we-know credits a frame it does not show
- Severity: minor
- Where: apps/web/app/how-we-know/page.tsx:14-40 and the kept and dropped cards; live /how-we-know.
- Compared: BlackBox shows the evidence where it makes the claim. The root cause screenshot tops its README, and examples/sample-incident/ holds the real patch.
- Evidence: The live page reads: "Frame v02-00127 ... the checker noticed: Stream shows straightened channel with cleared, uniform banks on right side ... The frame is a still from a video by Красота Приморского края и не только, CC-BY-3.0." Playwright finds no img inside main. examples/footage-flag/README.md shows both frames (photos/benchmark/v02-00127.jpg and v02-00143.jpg). It also shows that Sonnet 5 and Opus 5.5, which passed dug-out channels too, answered "no, no, no" on the kept frame, and that the frame has no label. The live page leaves all of that out, and the example opens only on Sep 30.
- Fix: Serve the two frames with the site and show each above its card with alt text. Add the example's line that the other passing models said no and that nobody has labelled the frame.

### D07. The kept status issue still says untrue things (partly fixed)
- Severity: minor
- Where: GitHub issue #4, public from Sep 30.
- Compared: BlackBox's only open PR is its receipt.
- Evidence: Issue #4 was last updated 2026-09-24T10:22:30Z. Under "What is live" it still says "three models ... 6 of 12 model and feature pairs passed ... the gate kept 33 of 63 candidate flags. Spent within the 40 dollar cap". Step 2 asks Alex to read `person_no_swallow`, which was dropped (DECISIONS.md:78). It also gives "1291 tests". The README now says four models, 9 of 16, 35 kept of 64 and 2020 Python tests. The model card says 41.1 USD, and DECISIONS.md:81 says the calls were not capped. The checklist part of the round 03 finding is fixed.
- Fix: Rewrite "What is live" and "What is green" with today's numbers, and drop step 2.

### F03. The judge Q&A says CI "has been green since" Sep 22; it was red on main on Sep 23 and 24
- Severity: minor
- Where: docs/submission/JUDGE_QA.md:91 (Q19), last edited at ac15c04 on Sep 24.
- Compared: BlackBox's CI section says what each push runs and links the workflow. It makes no claim about its history.
- Evidence: Q19 says "It was red on Sep 21 and 22 ... pull requests #2 and #3 fixed both, and it has been green since." gh run list shows the `check` workflow failing on pushes to main at 9f067a6 (2026-09-23T19:54Z), cd383d8 (2026-09-24T04:06Z) and 5ac66b0 (2026-09-24T07:33Z), and on depth at 08b98ee and 02bde2a. DECISIONS.md:92 records "CI on `main` was red at 5ac66b0". Main has been green since fb3ff24 (08:41Z). The answer sends the judge to the Actions tab, which lists those red runs.
- Fix: "It was red at times from Sep 21 to Sep 24 for reasons outside the product (a runner without the browser, a folder only the Mac had, a lockfile written by a newer npm); main has been green since fb3ff24."

### E02. Three docs still say every visit or every emitted resource validates (partly fixed)
- Severity: minor
- Where: docs/ARCHITECTURE.md:13 and :133-135; docs/adr/0005-fhir-under-oneaquahealth-profiles.md:23.
- Compared: BlackBox states the limits of its demo in its own words: "treat the incident realism as illustrative and the machinery as the contribution".
- Evidence: ARCHITECTURE.md:13 says "Every visit becomes FHIR that validates against their guide, carries the observer's score, lands in our store and mirrors to their sandbox." Line :133 says "`make check` fails if any emitted resource does not validate". ADR 0005:23 says "every emitted resource is checked by the HL7 validator in CI". results/fhir_validation.json lists 14 fixed files. The live walk says "This one was made on your phone and was not checked". A walk record is never stored and carries no score (F01). The sandbox has not resolved since Sep 23. The README and the Devpost text are fixed.
- Fix: Use the README's words in all three places: sample records from both emitters (14 files) are validated in CI, and golden vectors hold the live emitter to them.

### D05. Two pointers still send a judge to pages that cannot show the claim (partly fixed)
- Severity: cosmetic
- Where: README.md:561; docs/JUDGE_SCORECARD.md, Technical row "Their sandbox mirrored ...".
- Compared: every "where to look" in BlackBox's scorecard opens something that shows the claim.
- Evidence: README.md:561 says "`/city?creek=strawberry-creek`: what the creek needs, pipes worth testing with a FHIR referral, the downstream note by reach." Live, that page says "0 visits at 0 spots" and "No measure applies to what people have reported here so far." The /spot line above it got "It needs a stored record". The scorecard cites `/two` for the sandbox mirror, while live /two says "Their sandbox did not answer, so only our record is shown", and the Technical "Thin" line does not mention the outage.
- Fix: Add "(empty until the first real check; `make demo-offline` shows it)" to README.md:561. In the scorecard, cite `fhir/sandbox_ledger.jsonl` and `docs/notes/sandbox_library.md` in place of `/two`, and add the outage to Thin.

### E06. The report's subtitle still breaks badly (partly fixed)
- Severity: cosmetic
- Where: docs/REPORT.pdf page 1, from docs/report/template.html:15.
- Compared: Tideline's and BlackBox's title blocks each read whole on one line.
- Evidence: Rendered page 1 shows "A two-minute test that measures how well a volunteer sees a creek, and a vision model that may only" on one line and "ask" alone on the next. The PDF was rebuilt at 3ca393c and d870842 without this changing. Every other E06 slip is fixed.
- Fix: Shorten the subtitle, for example "A two-minute test of how well a volunteer sees a creek, and a model that may only ask", or put a non-breaking space before "ask".

### F04. New small wording slips
- Severity: cosmetic
- Where: apps/web/app/judges/page.tsx:51 and apps/web/app/about/page.tsx:11; README.md:434, :560 and :576; live /how-we-know; the walk's city view (/city?walk=v02).
- Compared: Tideline prints "98 tests" beside the command that prints them, and its claims match what the reader sees.
- Evidence: /judges and /about both open with the frozen landing line, "Two minutes teaching and testing you on the creek damage people usually miss.", two lines above the door that says "about four minutes with its lesson"; deviations.md:36 says "The /judges doors ... say about four minutes", which is true of the doors, not of the page's first line. README.md:576 says the walk's city page and `make demo-offline` "show the full view"; the walk's city view has only "What the checks found" and "What this creek needs": no pipes worth testing, no referral and no reaches. README.md:560 says "the gallery shows it on a local build", but the README's own Gallery (lines 74 to 90) has no /spot screen; it is in docs/screens/README.md. README.md:434 puts "The Bay Area plant list waits on a check ..." in the Where column, after the ADR link. Live /how-we-know names models by API id ("claude-haiku-4-5-20251001", "claude-fable-5-1"), while the README and the model card say "Claude Haiku 4.5". The walk's city view titles one finding with the raw question "Do you see any dams or other transversal artificial barriers?", next to "Pipes and drain outlets".
- Fix: On /judges and /about, show `judges.intro` or a line with no duration in place of `app.one_sentence`. README.md:576: "the page a walk opens shows what the creek needs; `make demo-offline` shows the full view". README.md:560: "docs/screens shows it on a local build". Move the plant-list sentence into the middle column of README.md:434. Show the models' display names on /how-we-know. Give barriers a short label, such as "Dams, weirs and grids".
