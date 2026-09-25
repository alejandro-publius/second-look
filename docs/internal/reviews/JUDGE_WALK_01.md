# Judge walk 01

Two subagents that wrote none of the product used Second Look the way a judge would on 2026-09-25 UTC, at commit 5420f3a: one on the live site (phone and desktop, throttled, and once with the network cut), one on the repository (the README as GitHub renders it, the judge docs, the report, and the Quickstart and `make judge-check` in a fresh clone). Each finding above cosmetic was then checked by a separate skeptic subagent. Everything they found that was slow, confusing, broken or unexplained is below, ranked worst first within each part, with the skeptic's verdict.

## The live site

I tested the live site as a judge would, on a phone profile (390x844 at 3x, Android Chrome UA, touch) and on desktop (1440x900). I used headless Google Chrome 153 through Playwright 1.63, because the clips are H.264. I read the repo at 5420f3a (the checkout moved from 4bfbb2a to 5420f3a while I worked) and edited nothing in it. Throttling (1.6 Mbps down, 750 kbps up, 150 ms RTT) came from a local CONNECT proxy, so the service worker was throttled too, plus CDP 4x CPU. The proxy only allowed second-look-79t.pages.dev and recorded zero connections to api.enora-oah.eu or sandbox.hl7europe.eu. A CDP Fetch guard on every page failed any non-GET request unless the run allowed it. Every script had its own deadline and ran in the background, writing to a log. Runs: A, the 45 second path on phone and desktop. B, the one sitting. C, /demo, /spot?id=example, /verify, /city?creek=strawberry-creek, bare /city, /two, /credits, /how-we-know and /about on both profiles. D, the walk /walk/v03 on the phone. E, /check on both profiles, stopped at Send. F, the network cut after the first load: proxy down plus browser offline. G, the desktop walk page, the stored record and the city view. I also ran small diagnostics: the offline page, the clip download without play, the landing image choice, and WebKit clip playback (it plays). Writes to the live site: (1) One sitting on the phone, trained arm, src=other, started 2026-09-25T17:48:55Z and finished. I filled the hidden bot-trap field so the pre-registered exclusion rule drops this automated session. /api/test/counts went from 0 to 1 randomized, 1 completed, so please tell the team. (2) One stored demo walk record, walk-fcaf2de6103a52c6, deleted 2026-10-25. The step asked for the stored record link, and that link only exists after the walk's own POST /api/walk. That POST was not on the list of allowed writes, so I allowed exactly it and its identical re-sends. An earlier attempt (walk-857dfdd327ab575a) was not stored: GET returns 404. (3) Nothing else. /check stopped on the Photos screen and Send was never pressed. Harness caveat: my first proxy had no backpressure and could reorder bytes. That caused one false 'You are offline' on desktop /verify, which I reproduced as an artifact and discarded, then fixed the proxy and reran everything except the sitting. So the sitting's first-photo time is an upper bound. Logs, text dumps and small screenshots are in /private/tmp/claude-501/-Users-alexvintera/69877729-e72a-4745-9745-aef366e01347/scratchpad/judgewalk/live-lens/ (run_a.log to run_g.log, text/, shots/).

### What worked

- The 45 second path is fast on a throttled phone: on a first visit the landing heading shows at 3.0 s and its photos at 3.8 s, /judges opens in 0.7 s and How we know in 0.6 s. Desktop is similar.
- Every page I tried rendered at 390 px with no horizontal scroll. The only console error was the expected 404 behind /spot?id=example.
- Once the service worker is in place, /demo, /verify, /city, /two, /credits, /how-we-know and /about show their heading in 0.3 to 0.8 s and settle within about 1 s on the throttled phone.
- /verify checks the three audit lines again in the browser in about 0.5 s and names Bitcoin block 968372 for each one.
- Judge mode's shut page is clear: it says why it is shut, gives the exact opening time in UTC and PDT, and links back to the judges' page.
- The walk works end to end. The record is built on the phone and says 'Every link inside the record checks out'. It is stored in 1.8 s with a delete date, and the link opens on a fresh device with the same answers and View as FHIR. The city view lists each measure with its Policy Brief page.
- The site is honest about the test and the demo data. /judges says the test counts as a session, walks say they store a demo record for 30 days, and /two says the sandbox did not answer.
- With the network cut after the first load, the landing and the creek check (through location and the questions) keep working. The 2.2 MB precache took about 11 s on the 1.6 Mbps line.
- The consent screen says plainly what is stored and has a working bot trap, which let me mark my automated sitting for exclusion.
- The browser never contacted api.enora-oah.eu or sandbox.hl7europe.eu: the proxy counted zero connections.

### Found, ranked

| Rank | Id | Kind | Severity | Skeptic | What |
|---|---|---|---|---|---|
| 1 | W01 | unexplained | major | confirmed, major | /judges advertises the creek check's 'follow-up questions picked by code' (the dry pipe question and the rating check), but a judge cannot see them without writing to the live database. In /check they only come back after Send, and Send first creates a real spot and a draft visit (createDraft calls resolveSpot and inserts into visit). The Photos screen says nothing about this. The walk, which /judges and JUDGE_DAY call the same creek check, runs no follow-up rules at all. |
| 2 | W02 | broken | major | confirmed, major | The score screen tells everyone 'Your score is saved with every creek check you make for the next 90 days.', including people who left 'Keep my score for creek visits' unticked. Without the token nothing links the score to later checks, so for them the sentence is untrue. It appears at the moment the product makes its main promise. |
| 3 | W03 | unexplained | major | not confirmed, minor | No page on the live site shows a real answer carrying its observer's per-feature score, which is the idea in the tagline. Walk records always say 'No score in a demo record', because the scores are hard-coded empty in worker/src/core/walks.ts, even for a judge who has just taken the test and kept the score. The gallery's sample record /spot?id=example does not answer, and the Berkeley city page is empty. The only instance is /two's 'Example record, made by hand for this demo'. |
| 4 | W04 | slow | major | confirmed, minor | Lesson and test photos are served as full-size JPEGs of 300 to 740 KB each, 21.1 MB for the 38 photos. The precache already holds 640 px AVIF copies of all of them (2.3 MB in total), but uses them only as offline fallbacks. On the throttled phone the photos lag behind their screens. |
| 5 | W05 | slow | minor | confirmed, minor | The v03 clip is 12.6 MB (H.264 High, 720p, 2.5 Mbps) for 40 s, more than a 1.6 Mbps line can carry, so it stutters. The host also answers a Range request with 200 and the whole file, so preload="metadata" pulls megabytes before anyone presses play and slows whatever the judge opens next. |
| 6 | W06 | unexplained | minor | not confirmed, cosmetic | Dug-out channel is one of the four features the test teaches and scores, and it appears on the score screen. But no check question maps to it (channel_form has feature: null), so this score can never travel with an observation. The live site mentions this only in passing, on /how-we-know. |
| 7 | W07 | slow | minor | not confirmed, cosmetic | The link a judge would open on a second device takes about 6.5 s to show the record on the throttled phone. Until the API answers, the page shows only 'Loading the record'. |
| 8 | W08 | confusing | minor | confirmed, minor | The README says the first-visit download is 'so the test and the creek check work offline'. But with the line cut after the first load, the README's own test link /t?src=other shows 'You are offline ... The test needs a connection.' Every judge page not yet visited shows the same page. It talks only about the creek check and 'this phone' (also on desktop) and offers only a Creek check link. |
| 9 | W09 | confusing | minor | confirmed, minor | The time quoted to a judge changes between consecutive screens. The landing says 'Find out in two minutes' and 'Two minutes teaching and testing you'. The consent screen right after it says 'It takes about four minutes', and /judges says 'about four minutes with its lesson'. |
| 10 | W10 | slow | minor | not confirmed, cosmetic | On a 390 px phone at 3x, the landing downloads the 1200w AVIF warm-up photos for images drawn 169 CSS px wide, because the img has no sizes attribute. Chrome also warns that the preloaded files went unused. That is about 430 KB of the 605 KB first load, roughly 2 s on the throttled line. |
| 11 | W11 | confusing | cosmetic | not checked (cosmetic) | The 43 credits read 'by <author>, <licence>, Source' with no photo title or thumbnail, so nobody can tell which photo a credit belongs to. The iNaturalist paragraph says 'What it said is next to each photo', but the page shows no photos. |
| 12 | W12 | slow | cosmetic | not checked (cosmetic) | On the throttled phone the Start the check button shows about 1.2 to 1.4 s before it responds. An early tap is dropped with no feedback. |
| 13 | W13 | confusing | cosmetic | not checked (cosmetic) | A judge who opens the bare site finds no judge entry: the page links only to About and 'Find out in two minutes', and For judges sits inside About. The labels 'This creek, on the left' and 'This creek, on the right' are the pick buttons, but they look like captions. |
| 14 | W14 | confusing | cosmetic | not checked (cosmetic) | Each walk question screen has two h1 headings, the creek name and the question, so a screen reader's heading list is ambiguous. |

#### W01

- Where: /check (Send on the Photos screen) and the walk record (/walk/v03); worker/src/check.ts createDraft; apps/web/components/WalkFlow.tsx
- Evidence: My walk answers were Overall rating Good, Bank type Artificial and sewage discharge Yes, which meets rating_check's trigger in content/followups.yaml. The walk still went straight from question 23 of 23 to 'Your record from the clip'. Neither the phone record nor the stored record /spot?id=walk-fcaf2de6103a52c6 has a 'Checks that ran' section. /check on both profiles: 23 questions, then Photos with only 'Optional. Photos are made smaller on your phone before they are sent. Location data is removed on the server.' and the buttons Add a photo, Back and Send. Without pressing Send, I could not reach the dry pipe question.
- Fix proposed: Run the same follow-up selection on walk answers (rain unknown, so dry_pipe fails closed and rating_check fires), and show the question plus 'Checks that ran' in the walk record. Also say on the Photos screen that Send adds a real spot to the live site before the follow-ups appear.

#### W02

- Where: /t score screen, apps/web/components/ScoreScreen.tsx line 97
- Evidence: In my sitting I did not tick Keep my score. The score screen (8 of 16 right, 2 of 4 on each feature) still showed the sentence and no token card. ScoreScreen.tsx always renders t("end.score_for"); only the token card is inside {token ? ...}.
- Fix proposed: Show the sentence only when a token was issued. Otherwise say the score was not kept and how to keep it next time.

#### W03

- Where: walk records (/walk/v03 and /spot?id=walk-...), /spot?id=example, /city?creek=strawberry-creek, /two
- Evidence: /spot?id=example on phone and desktop: GET /api/spot/example returns 404, and the page reads only 'Creek record' and 'No record for this spot.' (heading at 3.1 s on the phone), with no link onward. The stored walk record lists every tested feature as 'No score in a demo record'. docs/screens/README.md marks the sample record, its View as FHIR and its health card at /spot?id=example as (mock).
- Fix proposed: Seed a demo-tagged example spot so /spot?id=example answers on the live site. Let a walk record carry the scores of a token kept in the same browser, still tagged demo and never counted.

#### W04

- Where: /t lessons and the 16 test photos (components/ui/PhotoFrame.tsx: src={p.url}, no srcset)
- Evidence: The one sitting (phone, 1.6 Mbps, 150 ms, 4x CPU) pulled 23.4 MB through the line. Even with the next photo preloaded, photos 2 to 16 each took 0.6 to 4.0 s to appear after their screen. After a quick pass through the lessons, the first test photo appeared 54.6 s after its screen. That run used the proxy with the oversized buffer, so treat 54.6 s as an upper bound. Sizes by GET: ph-bank-06.jpg 605,157 B, ph-pipe-01.jpg 739,320 B, all 38 JPEGs 21,115,144 B.
- Fix proposed: Serve lesson and test photos as AVIF or WebP at 640 and 1200 px with srcset and sizes, and keep the full JPEG behind Enlarge.

#### W05

- Where: /walk/v03 (walks/v03.mp4; v07 is similar) and how the clip host handles Range
- Evidence: Played on the throttled phone: first frame 2.0 s after play, then 26 'waiting' stalls in 30 s, and only 19.7 s of video shown in 30 s. Without pressing play, opening /walk/v03 pulled 4.9 MB over 25 s, and /walk/v02 pulled its full 3.1 MB. Desktop /spot?id=walk-fcaf2de6103a52c6 opened just after /walk/v03 had TTFB 3.0 s and LCP 7.2 s. curl -r 0-1 on walks/v03.mp4 returns HTTP 200, content-length 12637217, and no Accept-Ranges. v07 is 15.0 MB. The /judges sample walk, v02, is the light one.
- Fix proposed: Re-encode the clips at 480p, about 800 kbps (roughly 4 MB), use preload="none" with the poster, and serve the clips from a host that honours byte ranges (for example R2 behind the Worker).

#### W06

- Where: /t score screen and the creek check (content/form.yaml)
- Evidence: The score screen lists 'Dug-out channel 2 of 4'. Walk and stored records mark Channel form 'Not a tested feature'. /how-we-know: '32 of the 35 kept flags are on a dug-out channel, which the check does not ask about, so they ask nothing.'
- Fix proposed: Add a straightened or dug-out question to the check, or say on the score screen and on /how-we-know that this score is not used yet, and why.

#### W07

- Where: The stored walk record link (/spot?id=walk-...) opened on another device
- Evidence: Fresh phone context, /spot?id=walk-fcaf2de6103a52c6: DCL 2.7 s, record heading at 6.5 s, LCP 6.2 s, 226 KB. By comparison the store itself took 1.8 s, View as FHIR opened in 0.1 s, and the city view with the record loaded in 1.8 s.
- Fix proposed: Start the /api/walk/{id} fetch from a small inline script before hydration, or have the Worker render the record's first screen as HTML.

#### W08

- Where: README 'Numbers at a glance' (the precache row) and the offline page
- Evidence: Network-cut run (phone, after the first load and a 2.2 MB precache that took 11 s): / and /check keep working (the check went through location and question 1 of 23). /t?src=other, /judges, /how-we-know, /demo, /walk, /walk/v03, /verify, /two, /city, /credits and /about all show 'You are offline'. For /t the cause is that the service worker keys pages by path and src, so /t?src=other misses the precached /t.
- Fix proposed: Reword the README row to 'so a test already started and the creek check keep working offline'. Give the offline page a home link and a line saying which pages open offline.

#### W09

- Where: / (landing), the /t consent screen, /judges
- Evidence: Text of / and /t?src=other on the live site, phone and desktop.
- Fix proposed: Use one figure everywhere, for example 'about four minutes with the lesson'.

#### W10

- Where: / on a phone (the two warm-up photos)
- Evidence: Phone fetched ph-warmup-03-1200.avif (191,199 B) and ph-warmup-04-1200.avif (238,745 B), rendered at 169 px with sizes empty. Desktop fetched 660w. Throttled phone first visit: heading at 3.0 s, photos at 3.8 s.
- Fix proposed: Give the img a sizes value that matches its real width (about 45vw on a phone, two photos side by side), so 660w is chosen, and keep the preload's imagesizes the same.

#### W11

- Where: /credits
- Evidence: /credits text and phone screenshot. document.images is 0 on the page.
- Fix proposed: Add each photo's title or a small thumbnail to its credit.

#### W12

- Where: /check intro, 'Start the check', on a first visit
- Evidence: Phone: button visible 1.39 s after navigation; the first tap that worked came 1.19 s later, on the 4th tap. Desktop: 1.44 s and 5 taps. In an earlier run a single tap 47 ms after the button appeared did nothing, and the page sat on the intro for 20 s.
- Fix proposed: Show the button disabled with a short 'Loading' until hydration, or make the first step a plain link that works before the scripts load.

#### W13

- Where: / (landing)
- Evidence: Landing links: Skip to content, Second Look, About, Find out in two minutes. Phone and desktop screenshots.
- Fix proposed: Add a small 'For judges' link on the landing until Oct 15, and style the two picks as buttons.

#### W14

- Where: /walk/v03 question screens
- Evidence: Desktop: 2 h1 elements, 'A creek in the United Kingdom' and 'Channel form'.
- Fix proposed: Make the creek name an h2 once the check starts, or make the question an h2.

## The repository

I read the README as GitHub renders it (gh api -X GET, html media type, ref=5420f3a) next to the raw markdown. Then I read docs/JUDGE_DAY.md, docs/JUDGE_SCORECARD.md, docs/submission/JUDGE_QA.md, WRITEUP.md, docs/MODEL_CARD.md and docs/REPORT.pdf (8 pages, text and small page images through PyMuPDF). I checked every README link, every cited test node id, every file path in backticks and every make target against the checkout. The read-only checkout's HEAD moved from 4bfbb2a to 5420f3a at 10:27:44 PDT, just as I started, and everything below is at 5420f3a. I cloned 5420f3a into /private/tmp/claude-501/-Users-alexvintera/69877729-e72a-4745-9745-aef366e01347/scratchpad/judgewalk/repo-lens/second-look with the push URL disabled. I ran the README Quickstart word for word, then make judge-check, in the background with a perl alarm deadline; the log is repo-lens/quickstart.log. In that clone I then ran make reproduce (reproduce.log), scripts/count_tests.py --print (counts.log), make verify-claims, verify_audit.py, ots_status.py (its results/ots.json change reverted), make new-city (reverted) and make demo-offline on spare ports, with one Playwright look at /city (demo_city.log, deadlines and load waits only). I cross-checked numbers against results/ and evals/fixtures/raw. On the live site I made GET requests only: 18 routes, /api/city/strawberry-creek, /api/two, /api/test/counts, /health and the /judges HTML. I sent no POST and made no call to api.enora-oah.eu or sandbox.hl7europe.eu. GitHub reads were gh api GET only, for CI runs on 5420f3a and hl7-eu/oah PR 5 and issues 6 to 8. Nothing in /Users/alexvintera/second-look-review was edited.

### What worked

- The README Quickstart ran word for word in a fresh clone of 5420f3a: clone 6 s, setup 13 s on warm caches, make judge-check 6 of 6 PASS in 276 s, offline, no key, and the tree was left clean.
- Every test node id cited in README, WRITEUP, MODEL_CARD, JUDGE_QA and JUDGE_SCORECARD exists, and every make target named exists.
- Every relative link in the GitHub-rendered README resolves, and no anchor is broken.
- make verify-claims passes (161 README claims), and both CI runs on 5420f3a finished green.
- make reproduce names each number it cannot regrade, with a reason, instead of skipping it silently in its own output.
- verify_audit.py reports the chain intact, and ots_status.py confirms all three timestamp proofs in Bitcoin block 968372.
- make demo-offline seeds its data with no network and renders a full /city with no console errors.
- make new-city scaffolds Aarhus in 0.32 s, as the README claims.
- hl7-eu/oah pull request 5 and issues 6, 7 and 8 exist and are open, as the README says.
- The MODEL_CARD quote 'possibly invasive Himalayan blackberry, but no stream is visible' appears word for word in the committed raw sweep replies.
- Known weaknesses are candid: one labeller, a key picked with a Claude chat, no human sessions yet, and plant photos with no water in them.
- The F86 fix is real: the Worker's /api/demo/answer returns 403 before the lock, and the README risk table says so correctly.
- REPORT.pdf renders cleanly at the 8 pages the README states.

### Found, ranked

| Rank | Id | Kind | Severity | Skeptic | What |
|---|---|---|---|---|---|
| 1 | R01 | broken | major | confirmed, minor | Four judge-facing documents say the Bay Area invasive plant list is a draft waiting for Rachel's check. They also say the plant question asks for Can't tell and the iNaturalist line reports none. At 5420f3a the list is approved and deployed, and the file the Q&A gives as proof does not exist. |
| 2 | R02 | unexplained | major | confirmed, major | The README says make reproduce "grades every AI number again from the committed raw replies ... and fails if one differs". The headline right-answer counts cannot be regraded, because the benchmark run behind them kept no replies. make reproduce says so in its own output, but judge-check's summary line drops that note. |
| 3 | R03 | unexplained | major | confirmed, major | The per-feature score is the product's trust signal. From Sep 28, judge mode says right or wrong on each of the same 16 photos, so anyone can rebuild the key and carry 4 of 4 on every feature into their creek checks. Retaking the test in a fresh browser does the same. The README calls the lock a protection ("so the answer key cannot leak before then") and never says what happens after it. |
| 4 | R04 | confusing | major | confirmed, minor | The test is a two-arm randomized trial. Half the people who press "Take the two-minute test" see the 16 photos first and are offered the lesson only after their score. The README never says so. It describes /t as "consent, the warm-up pair, the lesson, 16 items" and uses "arm" once without saying what it means. A judge placed in the untrained arm will think the lesson is missing. |
| 5 | R05 | broken | minor | confirmed, minor | Every test count in the README is stale at 5420f3a. These are the first numbers a judge compares after make judge-check, and they do not match. verify-claims passes only because it checks the README against a results file that was never regenerated. |
| 6 | R06 | confusing | minor | confirmed, minor | Working notes that stay public after go-public say things that are no longer true, and some read badly to a judge. They include a 'Still open' list with an answer-key leak and an AI-drafted health sentence under Alex's name, old AI results and cost, and a simulated 'six-judge rerun'. |
| 7 | R07 | confusing | minor | confirmed, minor | Reading top to bottom, a judge meets the gate, candidate flags, the pass table, the lock, judge mode, prereg-v1, golden vectors and walks in an 11-row numbers table before any of them is defined. The 'For judges' section starts at line 586 of 698, and a paragraph sits above the title. |
| 8 | R08 | unexplained | minor | confirmed, minor | The 9 expected failures in every test run are known bugs, marked strict xfail, in the gate, the FHIR emitter, the referral check, the follow-up selector and the content loader. The README shows "9 xfailed" and never says what they are. |
| 9 | R09 | unexplained | minor | confirmed, minor | The Wilson intervals the README tells judges to read treat 48 answers per model (12 per feature) as independent. They are really 3 runs over the same 16 photos, 4 per feature, and 3 of the 4 models cannot run at temperature 0. So the intervals are too narrow, and 'each beat the floor' of 24 of 48 is not supported for Haiku. |
| 10 | R10 | unexplained | minor | confirmed, minor | The README lists 'The ablation (rules only, context only, vision only, all three)' as one of the evals. The only ablation result is synthetic: stubs with a planted accuracy and the fake vision client. It cannot be regraded. |
| 11 | R11 | unexplained | minor | confirmed, minor | Several live features, including the data lock, run as eight launchd jobs on one laptop under Alex's own logins. The README says 'the Mac' as if the reader knows, and neither Feasibility nor Known weaknesses mentions it. |
| 12 | R12 | confusing | minor | confirmed, minor | The two docs written for judges are linked from neither the README nor /judges, so a judge will not find them. Once found, JUDGE_QA opens with "From pull request #5, checked against this branch", which reads like hl7-eu/oah pull request 5. JUDGE_DAY's 10-minute path starts with /demo but the README's does not, and "a failure is posted on the status issue" names no issue. |
| 13 | R13 | unexplained | minor | not confirmed, cosmetic | The Bitcoin timestamps are offered as proof that the plan came before the data. But all three proofs sit in a block after the paid model runs, so they do not back MODEL_CARD's 'fixed ... before any model ran'. The README's own ots verify command cannot finish without a Bitcoin node. |
| 14 | R14 | confusing | minor | not confirmed, cosmetic | The headline 'the gate dropped 29 of 64 candidate flags' reads as the AI working. But no kept flag would have asked a useful question: 32 of the 35 are on a feature the check never asks about, and 3 come from one model on one frame of water over stones. A judge learns this only in Known weaknesses. |
| 15 | R15 | unexplained | cosmetic | not checked (cosmetic) | The '0 errors' number and badge come from a validator run older than several emitter changes, and judge-check's offline 'fhir' step only reads that file. The 58 warnings are never mentioned, and 3 walks have only 2 validated walk records. |
| 16 | R16 | unexplained | cosmetic | not checked (cosmetic) | The README says 'The video is released under CC BY-SA 4.0' and credits its footage, but there is no link to any video at 5420f3a. |
| 17 | R17 | unexplained | cosmetic | not checked (cosmetic) | The README names Rachel Selbrede as a team member but says nothing about what she did. The public PLAN.md gives her the photos, the blind gold labels, the plant list and the health sentences, and DECISIONS turns every gate that named her into a team gate. A judge will ask. |
| 18 | R18 | unexplained | cosmetic | not checked (cosmetic) | The README says the demo API runs on port 8000 and documents only WEB_PORT. DEMO_API_PORT exists but is not mentioned, and unlike judge-check, demo-offline does not look for a free port. The Next dev server also listens on the LAN address, though the section says 'no network'. |
| 19 | R19 | slow | cosmetic | not checked (cosmetic) | judge-check prints nothing during its 229-second test step. Its final table shows only 'next build ok' for the web step, which hides the design-check result it printed above. |

#### R01

- Where: README.md lines 397 and 456; docs/submission/JUDGE_QA.md Q4 (line 20); docs/REPORT.pdf page 6; docs/HANDOFF_NEXT.md line 17
- Evidence: content/regions/california-bay-area.yaml has approved: true, approved_by "the team, Alex Velazquez, 2026-09-25" and 11 species (commit 285a757, 09:03 PDT today). docs/DECISIONS.md line 110 says the iNaturalist job stored 43 sightings of 6 listed plants for Strawberry Creek. content/form.yaml line 237 now asks "Which ones?". JUDGE_QA Q4 cites content/drafts/regions/california-bay-area.yaml, which is missing (the only missing path in all six judge docs), and calls the approved file "approved: false, empty". REPORT.pdf was built 2026-09-25T17:08Z, after the approval, and still says "the Bay Area list waits on a check, so it reports none yet". The approval commit updated docs/ALEX_TODO.md but none of these files.
- Fix proposed: Rewrite README lines 397 and 456, JUDGE_QA Q4 with its proof paths, and HANDOFF line 17 to say Alex approved the list for the team on Sep 25. Rebuild the PDF with make report-pdf. Add a claim token or test that ties the README sentence to the approved field so it cannot drift again.

#### R02

- Where: README.md line 505 (Evals) and line 563 (judge-check reproduce line); docs/submission/JUDGE_QA.md Q18; scripts/judge_check.py summary
- Evidence: evals/fixtures/raw/benchmark_20260924T054939Z.jsonl line 1: "kept": "the calls only: this run kept counts, not answers, so no reply survives". My make reproduce printed "note: the right-answer counts per feature, the share of cant_tell answers and the count of malformed replies are as recorded ... no reply is left to grade them from". make judge-check printed only "28603 values in 26 files regraded from raw replies and seeds ... every one matches". Affected: the README rows "Right answers, three runs" (31, 33, 33 and 34 of 48) and "without the plant photos" (of 36), plus the whole benchmark table and the Can't tell column in MODEL_CARD and REPORT.pdf 3.2. "Accuracies and intervals regraded" recomputes them from the recorded counts, which is circular.
- Fix proposed: Name the numbers that are recorded only, in the README Evals line and JUDGE_QA Q18. Make judge-check print the reproduce notes. Or rerun the benchmark and keep the replies (the four-model benchmark cost 2.2 USD per MODEL_CARD).

#### R03

- Where: README.md Known weaknesses line 654 and 'Why trust a volunteer'; docs/THREAT_MODEL.md lines 42 and 86; worker/src/index.ts lines 540 to 547
- Evidence: THREAT_MODEL line 42: "Rebuild the key after the lock, when judge mode says right or wrong | nothing ... | no: a volunteer who does this can carry a perfect score into their creek checks". Line 86: "The key can be rebuilt by retaking the test in fresh browsers". Once the lock passes, the Worker route returns {correct} for each item_id. The whole judging window, Oct 1 to 15, falls after the lock.
- Fix proposed: Put the THREAT_MODEL line into README Known weaknesses in plain words. Longer term, use a bank of photos so judge mode and retakes never show the photos that count, or mark a score from a browser that used judge mode.

#### R04

- Where: README.md line 503 ('per arm'), line 607 (/t flow), lines 21 and 34 (test links); docs/JUDGE_DAY.md; live /judges
- Evidence: docs/analysis_plan.md item 2: "Two arms, randomized 1 to 1 ... Untrained: test, then the lesson is offered afterwards". apps/web/components/TestFlow.tsx line 254 (untrained = !lesson_first) offers the lesson on the score screen. Live GET /api/test/counts returns "by_arm":{"untrained":...,"trained":...}. The /judges page says "Take the test, about four minutes with its lesson" and says nothing about the order.
- Fix proposed: Add one sentence under the test link and in JUDGE_DAY: you are placed at random in one of two groups, and one group sees the lesson after the photos. Define "arm" where it first appears.

#### R05

- Where: README.md lines 511 to 514 (Tests); WRITEUP.md lines 67 to 69; docs/ACCEPTANCE.md line 47; results/test_counts.json
- Evidence: README: 2056 Python tests, 125 golden cases in 15 node tests, 137 Playwright tests in 21 spec files, 14 Worker e2e sections. scripts/count_tests.py --print at 5420f3a: 2188 tests in 126 files, 133 cases in 16 node tests, 151 tests in 24 files, 15 sections. My judge-check printed "python: 2176 passed, 3 skipped, 9 xfailed" and "worker: pass 16". results/test_counts.json was generated 2026-09-25T04:33Z, and count_tests.py says it stays out of make check on purpose. JUDGE_QA Q17 says verify_claims "fails CI if one drifts".
- Fix proposed: Make make test-counts and make render-readme the last step before go-public (add them to submit-check). Or have judge-check compare its own counts with results/test_counts.json and say when they differ.

#### R06

- Where: docs/HANDOFF_NEXT.md lines 14 and 36 to 55; PLAN.md; Makefile lines 246 to 253 (scripts/go_public.py removes only docs/internal)
- Evidence: HANDOFF 'Still open' lists "F86, POST /api/demo/answer has no server lock check before Sep 28, so 16 POSTs reveal the gold key" (fixed: worker/src/index.ts line 543 now returns 403) and "F85, person_no_swallow was drafted by a session and carries Alex's name as approver" (dropped in cd50b1d). It also says "6 of 12 features passed, 13.09 USD of the 40 dollar cap"; today it is 9 of 16 features, and results/cost_log.jsonl sums to 41.11 USD over 5017 real calls. Line 14 reads "the six-judge rerun scored 7.33 against 5.73" and "Critic rounds 01 to 13". PLAN.md still names claude-opus-5 and Rachel's Sep 22 deliverables. The Makefile ai-run comment says the sweep "refuses above 10 dollars ... inside the 40 dollar cap", but the commands pass --max-usd 60 and 120. DECISIONS line 99 keeps these files public on purpose.
- Fix proposed: Put a one-line banner on HANDOFF_NEXT, PLAN.md and ALEX_TODO saying they are historical and pointing to the README. Strike or date the 'Still open' list, and fix the Makefile comment.

#### R07

- Where: README.md lines 1 to 140 and line 586
- Evidence: Line 44 says "the gate dropped 29 of 64 candidate flags", but the gate is defined only at line 147, and 'candidate flag' appears only in a diagram label (line 249). Line 72 says "before the lock"; the date first appears at line 543. "Judge mode" appears at line 133 and is defined at line 608. Line 59 says "each of the test's 38 photos", but the test has 16. Line 1 is a paragraph above "# Second Look".
- Fix proposed: Add a five-line glossary under the tagline (gate, pass table, flag, lock, judge mode, walk). Move 'For judges' up to just after the GIF, and say what the 38 photos are.

#### R08

- Where: README.md line 562 ('9 xfailed') and Known weaknesses; core/tests/test_harden_*.py
- Evidence: test_harden_fhir_emit.py line 494: "bug: a visit with no mapped answer gets a Provenance with an empty target list, which FHIR R4 forbids". test_harden_gate_properties.py line 624: "bug: an integer too big for a float raises inside the gate, so good flags drop too" (3 cases). test_harden_followups_properties.py line 404: "bug: on a confidence tie max() keeps the first flag, so list order picks the note". test_harden_fhir_referral.py lines 371, 383 and 397. test_harden_content_loader.py line 441. None of them appear in README, MODEL_CARD or WRITEUP.
- Fix proposed: Add one Known weaknesses line naming the 9 known bugs with their test ids, or fix the small ones before Sep 30.

#### R09

- Where: README.md line 44 ('Each beat the floor') and line 657 ('Read the intervals'); docs/MODEL_CARD.md benchmark table; results/benchmark_20260924T054939Z.json
- Evidence: Haiku: 31 of 48, wilson_95 [0.5044, 0.7657], against a floor of 0.5. Counted over 16 photos, that is about 0.41 to 0.83. A feature at 12 of 12 is 76 to 100 at n=12 but 51 to 100 at n=4. evals/models.yaml has accepts_temperature true only for claude-haiku-4-5-20251001.
- Fix proposed: Compute the intervals over photos (n=16 and n=4) or cluster by photo, and say so in the model card. Soften 'each beat the floor' to say it holds on point estimates only.

#### R10

- Where: README.md line 502 (Evals list); results/ablation_20260921T001415Z.json
- Evidence: The file's own note: "The rules and the context are stubs with a set accuracy and the vision signal is the fake client. Only the shape of the comparison is real", with stamp SYNTHETIC and vision_model claude-opus-5. make reproduce: "skip ... not regraded: its rule stub is keyed to the bytes of gray placeholder images the repository no longer has".
- Fix proposed: Mark the line as a synthetic shape that never ran on real models, or drop it.

#### R11

- Where: README.md lines 263, 613 and 655 ('the Mac'); DEPLOY.md lines 139 to 156; docs/ALEX_TODO.md step 6
- Evidence: DEPLOY.md lists com.secondlook.theirs (the /two cache), .inaturalist, .repush, .anchor, .uptime, .backup, .hl7 and com.secondlook.lock "once, at 18:10 on Sep 27 ... the data lock". ALEX_TODO step 6: "The data lock ..., the uptime check every 10 minutes and the daily jobs run only while it is awake."
- Fix proposed: Add one Known weaknesses line saying the daily jobs and the lock job run on one team member's Mac, and a Feasibility note on moving them to the Worker's cron.

#### R12

- Where: docs/JUDGE_DAY.md; docs/submission/JUDGE_QA.md; README 'For judges' table; live /judges
- Evidence: Searching README.md for JUDGE_DAY and JUDGE_QA finds nothing. The live /judges page links only MODEL_CARD, REPORT.pdf and examples/footage-flag. docs/DECISIONS.md line 65 shows the PR is this repository's own #5.
- Fix proposed: Add both docs to the README 'For judges' table and to /judges. Write "this repository's pull request #5" and "main". Link the status issue or drop the sentence.

#### R13

- Where: README.md risk table line 131; docs/MODEL_CARD.md 'The pass table'; proofs/README.md
- Evidence: ots_status.py in my clone: all three proofs confirmed at block 968372, block_time_utc 2026-09-24T08:35:54Z. The pass-table sweep was generated at 2026-09-24T05:47:56Z. proofs/README.md admits the stamps "do not prove the tag's own date"; the README does not. .venv/bin/ots verify proofs/prereg-v1.tag.ots exited 1 with "Could not connect to Bitcoin node" (the README does say it needs a node).
- Fix proposed: Say in the risk row that the stamp covers the human data lock only, and that the model rule's date rests on the git tag and GitHub's push record. List ots_status.py first as the command a judge can actually run.

#### R14

- Where: README.md line 44 and Numbers at a glance row 'Flags the gate stopped'; Known weaknesses line 650
- Evidence: results/footage_latest.json gate: kept 35, dropped 29. results/model_card.json footage_kept by feature: dug_out_channel 32, artificial_bank 3. README line 650. Line 159 says 0 of 3 walks shows a checker question, and the checker is off on the live site.
- Fix proposed: Put the outcome next to the headline number: of the 35 flags kept, none would have asked a volunteer a useful question.

#### R15

- Where: README line 15 (badge), line 70 and line 564; results/fhir_validation.json; docs/fhir_mapping.md line 3
- Evidence: results/fhir_validation.json: ran_at_utc 2026-09-24T03:30:19Z, warnings 58. The emitter changed after that run in bd423d4 (the Provenance source) and 3186aa7 (the walk row). fhir_mapping.md still says '0 errors, 15 warnings' from Sep 20. CI on 5420f3a (runs 36167264976 and 36167267914) passed and runs the validator, so the claim holds there.
- Fix proposed: Refresh results/fhir_validation.json with make fhir-validate before go-public. State the warning count and what the warnings are, and point judges to the CI run as the live check.

#### R16

- Where: README Credits line 676; For judges 'The demo script' row
- Evidence: The only video sources linked in README.md are the walk clips. docs/ALEX_TODO.md step 8 says the link goes in by Sep 29.
- Fix proposed: Add the link once the video is uploaded. Until then, say the video is coming on Sep 29.

#### R17

- Where: README 'How this was built' line 669; PLAN.md lines 144 to 149; docs/DECISIONS.md line 30
- Evidence: README: "every approval recorded in this repository is his. The team is Alex Velazquez and Rachel Selbrede." PLAN.md owner table, lines 144 to 149. DECISIONS 2026-09-21: "Every gate that named Rachel is a team gate".
- Fix proposed: Add one sentence on what Rachel actually contributed, or trim PLAN.md's owner table.

#### R18

- Where: README 'Running locally' lines 572 to 584; Makefile lines 28 to 32
- Evidence: lsof showed ssh already listening on *:8000 on this Mac, so I ran DEMO_API_PORT=8765 WEB_PORT=3187 make demo-offline. It worked: /city showed 3 visits at 2 spots and 1 pipe worth testing, with no console errors. Makefile line 29: DEMO_API_PORT ?= 8000. The demo log shows 'Network: http://192.168.1.240:3187'.
- Fix proposed: Document DEMO_API_PORT beside WEB_PORT, or pick a free port the way judge-check does.

#### R19

- Where: scripts/judge_check.py; README line 558
- Evidence: My run took 276 s in total, with the tests step at 228.8 s. The README's recorded run is 210 s at 9aee034, 39 commits earlier. Summary line: 'PASS web 18.4s next build ok'.
- Fix proposed: Print a start line for each step with its expected time, and join the sub-lines in the summary.

