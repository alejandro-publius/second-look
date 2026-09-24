# Critic round 02

Highest severity: blocker
Commit: 3b905a8

A critic subagent that wrote none of the code wrote this round on 2026-09-24 UTC, reading the repo at
3b905a8 read-only, the live site (which served the same commit) with GET requests only, and Alex's
two public repositories as the bar. Its report follows as it came back.

I read CRITIC_01 and the REVIEW_03 list first. Then I checked each round 01 finding at 3b905a8 with git log, diffs and greps. I cloned 3b905a8 fresh into my scratch folder, pointed PLAYWRIGHT_BROWSERS_PATH at an empty folder, and ran the README Quickstart word for word, then `make judge-check`. I shallow-cloned Tideline and BlackBox and read both READMEs, plus BlackBox's JUDGE_SCORECARD, ACCEPTANCE, DEVPOST and examples/sample-incident/. On the live site I used GET-only Playwright, with every non-GET request set to abort. None was attempted, and no request went to either forbidden host. I opened 21 routes at 390 px and 4 at 1440 px, and drove /walk/v02 through to its record and its city view. I compared the committed screenshots and the README GIF with the live pages, read docs/REPORT.pdf with pypdf, and read the GitHub state (PRs, branches, issues, CI) with gh. I checked every finding a second time before keeping it.

## Round 01, checked again
- C01: fixed. In a fresh clone, starting from an empty browser folder, the README Quickstart and then `make judge-check` printed "judge-check: 6 of 6 steps passed, offline, with no key". ACCEPTANCE's setup now installs Chromium and the worker's dependencies, and design-check names a missing browser.
- C02: fixed. The scorecard no longer says "still to come". Every "README, X" it cites is an existing heading, which scripts/tests/test_scorecard.py enforces. Impact's weakness line now says no person has taken the test.
- C03: partly. README, JUDGE_QA Q13 and the scorecard now agree. PLAN.md:165, deviations.md:12 and the missing ethics statement remain (D08).
- C04: partly. en.json, fhir_library.py, ig_proposal.md and the PR 5 body are fixed. The Library on their sandbox, and the read-back the README cites, still say "Berkeley, a follower city" (D09).
- C05: partly. See it work now says no real record exists, which is a stated limit. The Devpost demonstration field and the README judge path still promise /spot and /city content that the live pages do not have (D05).
- C06: partly. "The result, in short" now leads the numbers. The 31-screen gallery still comes before "Why trust", and See it work is at line 576 of 637 (D06).
- C07: fixed. The README has 173 relative links, none broken, and no repository path is left in backticks without a link.
- C08: partly. Gallery image 5 is now walk-city.webp, but that capture predates the R32 fix and shows the double count (D02).
- C09: still true (D03).
- C10: fixed. JUDGE_QA.md:16 now uses the DATA_CARD wording: the key came from the planner picks file, a Claude chat, and accuracy means agreement with that key.
- C11: partly. The README says 2003 Python tests, but pytest collects 2004 at 3b905a8. ACCEPTANCE still says 9 Worker e2e sections, not 13 (D16).
- C12: fixed. There is a new cost-per-question row (0.2 to 2.3 cents), and the 51.3 row now says what it multiplies.
- C13: fixed. The always-No floor (24 of 48) and the totals without plants are in the table, with claim markers.
- C14: fixed. The See it work row cites the read-back and the screenshot first, and marks the curl "when their name resolves again (hl7-eu/oah issue 8)".
- C15: still true in part. The Dependabot PRs are down to one (#17, green). The branches, issue #4 and the go_public removal list are unchanged (D07).
- C16: fixed. The five-box loop comes first, and the full system map is folded under it.
- C17: fixed. Remote main is 3b905a8 and CI is green. The live /verify shows "In Bitcoin block 968372". Live pages carry the fixed strings: /walk has "A creek in the United Kingdom", and /two has "Example record, made by hand for this demo".
- C18: fixed. The fixed tests badge is gone, and the licence, FHIR and guide badges each link their evidence.
- C19: fixed. The PDF has two figures (the gate and the FHIR records), no file name is split mid-word, and "this README" is gone.
- C20: still true (D10).
- C21: fixed. ADR 0008:11 now reads "Filming was dropped for time."
- C22: still true (D17).

## Where Second Look already meets or beats the bar
- `make judge-check` passed 6 of 6 in a fresh clone after the README Quickstart, starting from an empty Playwright browser folder: 47 s of setup, then 258 s. It now prints counts ("python: 1993 passed, 2 skipped, 9 xfailed", "worker: pass 15") and regrades 28603 values. BlackBox's judge-check regrades no model output.
- The README links every repository path it names: 173 relative links (111 distinct), all resolving. BlackBox has 57.
- The AI table now shows the floor to beat (24 of 48), the totals without the plant photos and the cost per question, each with a claim marker. BlackBox's scorecard lists cost per run as still unpublished.
- Every `path::test` cited in the README, JUDGE_QA, MODEL_CARD, THREAT_MODEL, ACCEPTANCE, WRITEUP, DATA_CARD, SECURITY and the scorecard exists: 0 missing.
- Model card, data card, threat model, 11 ADRs and an 11-part WRITEUP: more than both bar repositories have together.
- Live site: 21 routes each answered 200 in under 0.5 s, each with its own title, and none scrolls sideways at 390 px. The walk runs end to end. Its FHIR badge now says "This one was made on your phone and was not checked", and its city view counts pipes once.
- The stated limits now show on the pages themselves. /two says "No volunteer has sent a creek check yet." /city says "No measure applies to what people have reported here so far."
- /verify rechecks the audit chain in the browser and shows each proof in a Bitcoin block. Neither bar repository has anything like it.
- Contributed back: hl7-eu/oah PR 5, whose body now says the city has not adopted the method, and issues 6 to 8. BlackBox has two upstream PRs.
- CI was green on the 3b905a8 push to main, and the one open Dependabot PR is green.

## Findings
### D01. The real-vs-synthetic list the README calls "kept current" says the model pass table is synthetic
- Severity: blocker
- Where: docs/REAL_VS_SYNTHETIC.md:15, also :60
- Compared: BlackBox's "What's real vs. synthetic" is one list in its README. It agrees with its results, and its scorecard dates every change ("RESOLVED 2026-08-10").
- Evidence: README.md:503 says "The full list, kept current, is docs/REAL_VS_SYNTHETIC.md". Row 15 of that file reads: "The model pass table | synthetic | `"real": false` in the file; the checker refuses to flag on it | `results/model_pass_table.json`". results/model_pass_table.json has `"real": true`, generated 2026-09-24T05:47:56Z. The same file contradicts itself: line 12 says "the AI table is real since Sep 23 and 24". The row has not changed since 634d0e6 on Sep 20. Line 60 says "whether the three models agree", but four models ran. This is the same class of error as round 01's C02, a judge-facing doc saying the AI result is not real.
- Fix: Change row 15 to "real, from the paid sweep of Sep 23 Pacific time; the file says "real": true, and a table without it licenses nothing". Change "three" to "four" on line 60. To prove it: add REAL_VS_SYNTHETIC.md to a test that reads the pass table's `real` flag and fails when the row says synthetic.

### D02. Eight gallery screens and the README GIF predate the fixes, and show text the live site no longer has (C08 partly)
- Severity: major
- Where: docs/screens/about.webp, how-we-know.webp, walk-city.webp, city.webp, two.webp, judges.webp, demo.webp, consent.webp and two-minute-test.gif; README.md:36 and :78-126; docs/devpost.md:173
- Compared: BlackBox's screenshots show the product as shipped, captioned with its result ("verified repair (32/32, real diff, git branch)").
- Evidence: git log shows each screen last committed between Sep 23 23:34 and Sep 24 02:29 PDT. The fixes landed between 03:15 and 03:59 (bbef994, 9bdd7b2, 5d97360, a1a243c, 1de5fef, a8fdd46, 7e3d758, 20abb0e). The last commit, 3b905a8, did not rerun `make screens`. about.webp reads "Berkeley is a follower city.", the untrue C04 sentence; live /about says "though the city has not adopted it". how-we-know.webp reads "prereg-v1 (not yet tagged)". walk-city.webp, which is Devpost gallery image 5, reads "Checks from this phone: 1" above "Pipes and drain outlets / Checks that saw it: 2"; my live walk, answering Yes to both pipe questions, now shows 1. city.webp reads "nobody has approved one". two.webp shows "Location/sl-loc-spot-1" and no example label. judges.webp shows "The same creek beside...". demo.webp shows two dates, Sep 28 in the heading and Sep 27 in the text. consent.webp, and frame 1 of the GIF (the first image in the README), read "your device type and the version of this text. Nothing else.", without "the kind of link you came from". README.md:76 still says "24 come from the live site".
- Fix: Run `make screens` against the live site, which now serves 3b905a8, and commit the results. Add a submit-check item that fails when content/locales/en.json or apps/web/app changed after the oldest live screen's commit.

### D03. C09 still true: a judge on the live site reaches no evidence, and /how-we-know shows no number
- Severity: major
- Where: apps/web/app/page.tsx, apps/web/app/about/page.tsx, apps/web/app/judges/page.tsx:14-26, apps/web/app/how-we-know/page.tsx, content/locales/en.json:310
- Compared: BlackBox's "For judges" section gives a 45-second path, pastes its check output, and links each proof from a table.
- Evidence: from the live site with GET only, / links only "/t" (plus About); /about links /t, /privacy, /how-we-know, /credits and /accessibility, but not /judges; /judges has ten links, only one with a line of text, none to the repository, the README, REPORT.pdf, the model card or results (the string "judges.repo": "The code" exists in en.json:424 but is never rendered); /how-we-know has 0 links and no number; /privacy names "docs/DATA_HANDLING.md in the repository" as plain text.
- Fix: Render the existing "The code" door on /judges, pointing at the repository, which opens Sep 30. Add links to README#for-judges, REPORT.pdf and MODEL_CARD, and give each door one line saying what it proves and how long it takes. Link /judges from /about. Render the pass table and the gate's 29 of 64 into /how-we-know from results/ at build time.

### D04. Nothing a judge can open shows the AI act: no screen, page or example shows a gated flag or "the checker noticed"
- Severity: major
- Where: README.md:187, results/screens.json, examples/, apps/web/app/judges/page.tsx
- Compared: BlackBox shows its agent working at the top of its README (02-investigation.png, 03-rootcause.png). examples/sample-incident/ holds the unedited transcript and the patch.
- Evidence: README.md:187 says "Where it runs today: nowhere a person sees yet." The live /check runs with the checker off. The live /walk/v02 ends with "The checker asked nothing ... 0 of its guesses on this clip were stopped for that reason". The only gallery screen that mentions the checker is walk-record.webp, and it says the same. examples/ holds only mcp/, and /judges has no AI door. For a Track 3 entry, the model's work is visible only in the README tables and in the raw lines of evals/fixtures/raw/*.jsonl.
- Fix: Commit examples/footage-flag/ with one footage frame where the gate kept a flag and one where it dropped one. Include each frame's raw reply line from evals/fixtures/raw/footage_20260924T060539Z.jsonl, the gate's Flag or its drop reason, and the follow-up question the kept flag makes eligible. Add one (mock) gallery screen of that question with its "the checker noticed" note, and link both from See it work and /judges.

### D05. C05 still true in the Devpost text and the judge path: /spot and /city are promised with content they do not have
- Severity: major
- Where: docs/devpost.md:98-99, :172; README.md:552; apps/web/app/judges/page.tsx:23; docs/video/VOICE_SCRIPT.md beat 12
- Compared: BlackBox's demonstration points at a run a judge can open: examples/sample-incident/ and PR #1.
- Evidence: devpost.md:98 says "/spot: the record, each answer beside the observer's score, View as FHIR with the validation badge, the health card." Live /spot says "This link names no spot.", and /spot?id=example says "No record for this spot." (a 404 on /api/spot/example). devpost.md:99 says "/city: ... with what the creek needs in OneAquaHealth's own measures." Live /city?creek=strawberry-creek says "0 visits at 0 spots ... No measure applies". Gallery image 4 (spot-record.webp) comes from the mock build; the README marks it "(mock)", devpost.md does not. The README's own See it work says the full city view is /city?walk=v02, but its judge path (README.md:552) and the "For a city" door on /judges both open the empty creek. VOICE_SCRIPT beat 12 says "The creek page lists what it needs" over a shot of that empty page.
- Fix: In devpost.md, replace the two lines with the walk: "/walk/v02, then See this creek as a city would: the record your answers make and what the creek needs, in OneAquaHealth's measures". Add "/city?creek=strawberry-creek stays empty until the first real check". Label image 4 "sample record, local build". Point the README path step and the /judges door at the walk's city view, and shoot beat 12 from /city?walk=v02.

### D06. C06 partly: the README grew, and 31 screens still stand between the result and "Why trust"
- Severity: minor
- Where: README.md:74-137, README.md:576
- Compared: BlackBox's README is 297 lines (26 KB), with See it work at line 38 and Why trust at line 58. Tideline's is 260 lines.
- Evidence: The README is now 637 lines and 77,041 bytes, up from 611 lines at a52de70. The 31-screen table fills lines 78 to 126 before "Why trust" at 139. See it work is at line 576.
- Fix: Keep five screens in the README (landing, score, walk, walk record, walk city) and move the other 26 to docs/screens/README.md. Move "What was built, screen by screen" up under Numbers at a glance.

### D07. C15 still true: working branches, a "For Alex" status issue and three working notes stay public
- Severity: minor
- Where: GitHub branches and issue #4; scripts/go_public.py:161; docs/ALEX_TODO.md, docs/HANDOFF_NEXT.md, docs/SUBMISSION_CHECKLIST.md
- Compared: BlackBox has two branches, and its only open PR is its receipt.
- Evidence: gh lists 8 working branches: ci-depth, ci-main, depth, finish, harden, p27/integrate, polish and takeover. Issue #4, "Status: Second Look", is open (updated 2026-09-24T10:22Z) and starts "For Alex, Sep 24". It asks him to read person_no_swallow: "It carries your name as approver but a session drafted the wording". That sentence was dropped in cd50b1d on Sep 23. A public reader would read it next to README.md:610, "approved every sentence a person reads". go_public runs `git rm` only on docs/internal. So ALEX_TODO ("add about 300 dollars", "Copy that key and your API key to your password manager") and HANDOFF_NEXT ("the critic rounds against Alex's tideline and blackbox-datahub READMEs") stay in the public tip.
- Fix: Close issue #4, delete the merged working branches, and move the three files under docs/internal or add them to go_public's removal list.

### D08. C03 partly: PLAN.md still says nobody is recruited, the deviation log says the panel is not paid by us, and no public doc states the ethics position
- Severity: minor
- Where: PLAN.md:165 and :181, docs/DECISIONS.md:42, docs/deviations.md:12, content/locales/en.json:12
- Compared: BlackBox says "PR publication is wired but opt-in" in the same words in its README and ACCEPTANCE.
- Evidence: PLAN.md:165 still reads "Nobody is recruited". The one-voice test in scripts/tests/test_scorecard.py reads only README, docs/*.md, JUDGE_QA and the report source, and skips DECISIONS and deviations. deviations.md:12 says "Panel members are paid by the panel, not by us, and nobody is recruited by us", but ALEX_TODO.md:28 has Alex "add about 300 dollars" to Prolific and publish the study. ALEX_TODO says "The panel asks about ethics approval", yet no public doc says whether a review or an exemption applies.
- Fix: Add one dated line to deviations.md: "If Alex launches it, we fund Prolific for up to N sessions and Prolific pays the participants". State the ethics position in the same line and under Known weaknesses. Reword PLAN.md:165 and :181.

### D09. C04 partly: the sandbox copy of the Library, and the read-back the README cites, still say "Berkeley, a follower city"
- Severity: minor
- Where: docs/notes/sandbox_library.md:33, :70, :74; core/fhir_library.py:78-80
- Compared: BlackBox's README says outright that its incident realism is illustrative.
- Evidence: README See it work cites docs/notes/sandbox_library.md as proof of "What went to their sandbox". Its Library reads "citizen creek checks from Berkeley, a follower city ... 1 visit records mirrored", with the author "Second Look project, Berkeley, a follower city". It does not say the one visit is the hand-made example. The note does not say the wording has changed since. fhir/golden/library-second-look.json now says "run the way a follower city would ... a hand-made example". The generator writes "1 visit records".
- Fix: Put two lines at the top of the note: what the sandbox copy says, what the corrected Library says, and that the allowed conditional update waits on issue 8. Make the count agree in number ("1 visit record").

### D10. C20 still true: the README describes judge-check but does not show its output
- Severity: minor
- Where: README.md:534
- Compared: BlackBox's README pastes its five-line "BLACKBOX JUDGE CHECK" block with counts.
- Evidence: my run printed six PASS lines, including "tests ... python: 1993 passed, 2 skipped, 9 xfailed", and ended "judge-check: 6 of 6 steps passed, offline, with no key" after 258 s. The README says only "six steps, each printed with ok or FAIL".
- Fix: Paste the six PASS lines under the Quickstart, with the counts as claim markers from results/test_counts.json, and say it takes about five minutes after setup.

### D11. REVIEW_03 R36 still true on the site: every door says two minutes and the consent says four
- Severity: minor
- Where: content/locales/en.json:5, :9, :417, :421; README.md:21
- Compared: BlackBox gives its run one duration (about 180 s) and uses it everywhere.
- Evidence: Live / says "Find out in two minutes", and the next screen says "It takes about four minutes." /judges has "Take the two minute test" and "a one-minute video walk". The walk is a 40 s clip followed by 23 question screens in my run. /poster says "Two minutes." README.md:21 says "the two-minute test (about four minutes with its lesson)".
- Fix: On /judges, the poster and the README, say "about four minutes". Relabel the walk door "a 40 second clip, then the full check". Log the landing button, which is a frozen string, as a known mismatch in deviations.md.

### D12. SECURITY.md says the consent screen links the data handling doc and that no free text is kept; neither is true
- Severity: minor
- Where: SECURITY.md:4, SECURITY.md:33
- Compared: BlackBox's ACCEPTANCE states each limitation the same way its README does.
- Evidence: SECURITY.md:4 says "docs/DATA_HANDLING.md, which the consent screen links to", but live consent has one link, "Back", to "/" (Consent.tsx:37). SECURITY.md:33, under "What we never keep", says "Free text from a person. Every answer is a choice from a list." README.md:518, /privacy and DATA_HANDLING.md:51 all say the name typed for a new spot is stored and public. REVIEW_03 R10 and R19 were fixed everywhere except here.
- Fix: Change the first to "which /privacy points to", and the second to "Free text, except the name typed for a new spot, which is public".

### D13. The Devpost AI paragraph says the footage pipeline is "ready for" 46 frames, and leaves out what the gate did
- Severity: minor
- Where: docs/devpost.md:79
- Compared: BlackBox's DEVPOST.md states its demo result in one line.
- Evidence: devpost.md:79 says "the same pipeline is ready for 46 frames from 5 openly licensed creek videos". results/footage_latest.json is real, and README.md:44 says "On 46 frames of real creek footage the gate dropped 29 of 64 candidate flags". The field has markers for frames, videos and countries, but none for the gate.
- Fix: Write "and ran on 46 frames ...: the gate dropped 29 of 64 candidate flags, each for a feature that model had not passed", with claim markers on footage_latest.json#/gate/dropped and /candidates.

### D14. The README's For judges table sends judges to a superseded video script
- Severity: minor
- Where: README.md:563
- Compared: BlackBox's For judges table links docs/DEMO_SCRIPT.md, its current walkthrough.
- Evidence: the row "The demo script" links docs/video_script.md. That file opens with "Superseded by docs/video/SHOTLIST.md". Its rows still plan "Over the shoulder of a real person at Strawberry Creek" and a shot of /spot?id=example.
- Fix: Link docs/video/SHOTLIST.md, or docs/video/VOICE_SCRIPT.md, instead.

### D15. The Quickstart names no prerequisites
- Severity: minor
- Where: README.md:526-534
- Compared: BlackBox's Quickstart opens with a Prereqs line (Python 3.11 or later via uv, Node 20 or later). Tideline states Python 3.11 or later and Node 20 or later beside its commands.
- Evidence: the first command after the clone is `uv sync`, and nothing says uv, npm or which Node version is needed. The web build uses Next.js 16, and CI pins Node 20 for it (check.yml). No package.json has an engines field.
- Fix: Add one line above the block: "Needs git, uv (it fetches Python 3.12) and Node 20 or later with npm; no Java, no key."

### D16. C11 partly: the test counts are off by one, and ACCEPTANCE keeps an old section count
- Severity: cosmetic
- Where: README.md:495, results/test_counts.json, docs/ACCEPTANCE.md:45
- Compared: Tideline prints "98 tests" beside the command that prints it.
- Evidence: the README says 2003 Python tests, but at 3b905a8 `uv run pytest --collect-only -q` sums to 2004, and judge-check ran 1993 passed, 2 skipped and 9 xfailed. test_counts.json says `"measured_at_commit": "950ccad"` and `"tree_had_changes": true`. ACCEPTANCE row 18 says "9 sections green", while results/test_counts.json lists 13.
- Fix: Run `make test-counts` on a clean tree at the last commit. Have ACCEPTANCE's row 18 read its count from results/test_counts.json, and have judge-check warn when its count differs.

### D17. C22 still true: CI is one job, and one of its comments is out of date
- Severity: cosmetic
- Where: .github/workflows/check.yml:7, :60
- Compared: BlackBox's ci.yml has five named jobs.
- Evidence: there is one job, `check`, which runs make check, make reproduce, make e2e and the Worker e2e. A comment still says "The Worker's package and its e2e live on depth until depth merges", but depth has merged.
- Fix: Split it into python, reproduce, web-e2e and worker-e2e jobs, and drop the stale comment.

### D18. Small wording slips in the README and the docs
- Severity: cosmetic
- Where: README.md:578, :428, :452; docs/ARCHITECTURE.md:3; docs/submission/JUDGE_QA.md:87
- Compared: BlackBox links each proof to the file it names.
- Evidence: README.md:578 says "the table of what is real and what is synthetic below says", but the table is above, at line 501. README.md:428 links the MCP payload field `fhir` to the fhir/ folder. README.md:452 links README.md to itself. ARCHITECTURE.md:3 says "The README has the three diagrams"; it has four. JUDGE_QA Q18 says judge-check runs "FHIR validation against the pinned guide", but it only reads the last run, as README.md:534 says.
- Fix: Change "below" to "above". Unlink `fhir`, and drop the self-link. Change "three" to "four". In Q18, say "reads the last HL7 validator run".
