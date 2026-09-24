# Adversarial review 03

Reviewer subagents that wrote none of the code wrote this review on 2026-09-24 UTC. They read the
repo at commit 3fa942f on `p29/integrate`, the tree that holds every UPDATE_29 file
(`docs/MODEL_CARD.md`, `docs/THREAT_MODEL.md`, `docs/DATA_CARD.md`, `docs/internal/PANEL_STUDY.md`),
with production deployed from the same code, and checked it against the hard rules in `CLAUDE.md`,
UPDATE_27 and UPDATE_29. Commit: 3fa942f

How it ran:

- Four finders, each with one lens: the hard rules, privacy and security; every claim against the
  code and `results/`; what a judge meets in the first ten minutes, on the live site with GET
  requests only; and tests that would pass with the thing they guard removed. Each finding had to
  carry evidence from a file, a command or a live GET.
- Then one skeptic per finding, told to refute it. The skeptics checked 15 findings and confirmed
  all 15, moving two ranks (R07 down to cosmetic, R11 up to should fix). The skeptic stage was
  stopped there, because it held every subagent slot the fixes needed. Each of the other 44 was
  reproduced by the session or the agent that fixed it, before the fix; a finding that did not
  reproduce is marked refuted below with the evidence.
- Every fix that changes behaviour has a test, and each test was broken on purpose to see it go
  red. Frozen parts were kept: the 16 study functions of the Worker are byte for byte those of
  `prereg-v1`, and the consent change is logged in `docs/deviations.md` (no participant had
  consented; the public counts read 0).

## Counts

| Rank | Found | Fixed | Refuted | Not fixed |
|---|---|---|---|---|
| Breaks a hard rule | 3 | 3 | 0 | 0 |
| Could lose data | 1 | 1 | 0 | 0 |
| Should fix | 35 | 35 | 0 | 0 |
| Cosmetic | 20 | 20 | 0 | 0 |

## The most serious, in plain words

- **R01, breaks a hard rule.** DATA_HANDLING still says the Worker logs keep only the path, but they keep the whole request URL (REVIEW_02 F02 and F46, still true). The data handling page said the API's logs keep only the path; they keep the whole address. The page now says so.
- **R02, could lose data.** GET /api/skeleton still writes a D1 row on any method (REVIEW_02 F87, still true). Any GET to an old test route on the live API wrote a row to the database. The route is gone, and a test proves a GET and a POST both get 404 and write nothing.
- **R12, breaks a hard rule.** Worker JPEG cut still keeps GPS, while README, WRITEUP and Devpost say uploads are stripped. A photo sent straight to the upload route could keep its camera's GPS in three JPEG shapes phones make. The Worker now cuts them all, or refuses the file.
- **R26, breaks a hard rule.** The credits page scrolls sideways on a phone and squeezes author names to one word per line.

## Every finding

### R01. DATA_HANDLING still says the Worker logs keep only the path, but they keep the whole request URL (REVIEW_02 F02 and F46, still true)

- **Rank:** breaks a hard rule (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `docs/DATA_HANDLING.md:67`
- **Evidence:** worker/wrangler.jsonc has "observability": { "enabled": true }. docs/DATA_HANDLING.md:66-67 says: "Those traces hold the path and the response code." Cloudflare's Workers Logs page (developers.cloudflare.com/workers/observability/logs/workers-logs) says: "Each Workers invocation returns a single invocation log that contains details such as the Request, Response, and related metadata ... Fetch requests will have a message describing the request method and the request URL". These logs are kept for up to 7 days. The export token travels in the URL (worker/src/index.ts:537 url.searchParams.get("token")), and so do photo tokens as ?t= (:470). Nothing in the history since REVIEW_02 changes these lines, and patch 02 was never applied (REVIEW_02 patches section: "None has been applied anywhere"; HANDOFF_NEXT.md:54-62 does not list it as done).
- **Outcome:** fixed. bbef994: `docs/DATA_HANDLING.md` now says the Workers logs hold each request's method and full address with its query string, so the photo and export tokens, for up to 7 days; the edge records the address with its query string.

### R02. GET /api/skeleton still writes a D1 row on any method (REVIEW_02 F87, still true)

- **Rank:** could lose data (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `worker/src/index.ts:452`
- **Evidence:** worker/src/index.ts:451-456: `if (path === "/api/skeleton") { ... INSERT INTO skeleton_ping ... SELECT COUNT(*) AS n FROM skeleton_ping ... }` with no method check. apps/web/functions/api/[[path]].js forwards every /api/* request on the Pages origin to the Worker unchanged, so the route can be reached at https://second-look-79t.pages.dev/api/skeleton. I did not probe it live, because a GET there writes to production. Patch 14 was never applied.
- **Outcome:** fixed. Commit 8eded9b. Deleted the /api/skeleton branch from worker/src/index.ts. Regenerated results/api_inventory.json (the Worker now has 25 routes) and re-rendered README.md and docs/API.md from it. Removed the route's row from docs/API.md and fixed SECURITY.md known gaps, the THREAT_MODEL read-quota row, docs/notes/hosting.md (P1 now in the past tense) and the DEPLOY.md skeleton_ping row. Logged in docs/deviations.md.
- **Proof:** worker/test/e2e.mjs, new section "an empty store": GET and POST /api/skeleton both return 404, and a local D1 query finds 0 rows in skeleton_ping. Mutation: I put the skeleton route back into index.ts, and the e2e failed at "an empty store" (actual 200, expected 404).

### R03. The service worker stores the panel id from the link in the phone's cache

- **Rank:** should fix (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `apps/web/public/sw.js:78`
- **Evidence:** sw.js:63 sends every navigation to networkFirst, and :78 calls cache.put(req, res.clone()), keyed by the full request URL. I ran a GET-only headless Chromium on the live site: opened https://second-look-79t.pages.dev/t?src=panel&PROLIFIC_PID=zzreviewfakepid42&STUDY_ID=st1&SESSION_ID=se1 twice. The address bar became /t?src=panel, but the caches printed: "cache sl-c78d66bb4173c27a-runtime: 11 entries, with panel id: [\"https://second-look-79t.pages.dev/t?src=panel&PROLIFIC_PID=zzreviewfakepid42&STUDY_ID=st1&SESSION_ID=se1\"]". The service worker also sent that URL to the network again (the request log shows it with sw=1). This happens on any visit after the service worker has installed, not on the very first. The test cannot see it: apps/web/playwright.config.ts:19 sets serviceWorkers: "block", and panel.spec.ts:41 checks only sessionStorage and localStorage. docs/deviations.md:12 says "no panel identifier is ever stored or sent", and docs/internal/PANEL_STUDY.md:42 says "Nothing from the panel's link but src is stored or sent".
- **Outcome:** fixed. 67bfa04: apps/web/public/sw.js caches a navigation under pageKey(req), which is the origin and path plus src only. The fetch itself is unchanged. Added the test to apps/web/tests/panel.spec.ts, a clause to docs/internal/PANEL_STUDY.md and a line to docs/deviations.md.
- **Proof:** panel.spec.ts 'a panel link opened twice leaves no panel identifier in any cache' (service worker allowed). Mutation: set `const key = req;` in networkFirst (the cache key is the full request again). The test went red with 'Expected substring: not "pid5f3a9"'. Restored, and it passed.

### R04. The panel consent sentence says nothing about you is stored, right under the list of what is stored

- **Rank:** should fix (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `content/locales/en.json:12`
- **Evidence:** en.json:10 consent.stored: "We store: a random session id, which group you were in, your answers, how long each screen took, a hashed random browser token, your device type and the version of this text. Nothing else." en.json:12 consent.panel: "You are taking part through a research panel and will be paid by the panel; nothing about you is stored here." Consent.tsx:44-48 renders both on the same screen. "Nothing else" also leaves out the source label, which for this group is panel. The live run showed sessionStorage {"sl_src":"panel"}, and createSession stores it (REVIEW_02 F31, still true).
- **Outcome:** fixed. bbef994: the panel's sentence reads "nothing that identifies you is stored here"; `docs/deviations.md` logs it with the consent version change. No participant had seen the old text.
- **Proof:** `apps/web/tests/panel.spec.ts` and `scripts/done_items.py panel-prep` hold the new sentence.

### R05. The privacy page and the data docs still list five source labels, not panel

- **Rank:** should fix (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `content/locales/en.json:298`
- **Evidence:** A live GET of /privacy returns: "A coarse label from the link you used: poster, chat, friends, creek group or other." docs/DATA_HANDLING.md:15 has the same five labels. docs/CONTRACTS.md:54 says: "source_label is coerced to one of poster, chat, friends, creek_group, other". But worker/src/index.ts SOURCE_LABELS now includes "panel", and the live /api/test/counts returns "by_source":{...,"panel":0}. Also, DATA_HANDLING.md:62 says Cloudflare's edge keeps "the requested path", while PANEL_STUDY.md:43-45 admits that the first page request carries the whole link, panel id included. DATA_HANDLING does not say so.
- **Outcome:** fixed. bbef994: the privacy page, `docs/DATA_HANDLING.md` and `docs/CONTRACTS.md` list panel among the link labels; DATA_HANDLING says a panel's own identifiers reach Cloudflare's edge in the first page request.

### R06. The panel completion code is a fixed string that anyone can read in the public page code

- **Rank:** should fix (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `apps/web/lib/panel.ts:11`
- **Evidence:** A live GET of the /t chunk 0nxjs0xdsa_5r.js contains: `"data-testid":"panel-code",children:(0,c.t)("end.panel_code",{code:"SLCREEK26"})`. By design, no panel id is kept, so a panel submission cannot be matched to a session (PANEL_STUDY.md). A code pasted without doing the test therefore cannot be rejected, and the 80 paid places can fill with fewer real sessions. Sessions under 40 seconds, which the plan excludes, also get the code.
- **Outcome:** fixed. 9155c53: as instructed, no new route. docs/internal/PANEL_STUDY.md gets step 4: before approving any payment, compare the panel's count of submitted codes with the completed panel sessions `make panel-status` prints. The same step says the code is visible in the page source, so a code alone does not prove a finished session, and that the analysis counts only finished sessions. Step 3 no longer says 'Nothing else is needed'. scripts/done_items.py check_panel_prep now requires those three statements.
- **Proof:** scripts/tests/test_done_items.py::test_the_panel_study_checks_codes_against_finished_sessions_before_paying (the real tree passes; copies without the step or without 'page source' fail, each naming its gap). Mutation: deleted step 4 from the real PANEL_STUDY.md, and the test went red (check_panel_prep returned the missing-step problems). Restored, and it passed.

### R07. The iNaturalist line opens per creek, so later volunteers see it before they answer the plant question

- **Rank:** cosmetic (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `worker/src/inaturalist.ts:78`
- **Evidence:** invasiveAnswered (worker/src/inaturalist.ts:78-89, used at :113) returns true once any finished visit at any spot on the creek has an invasive_species answer. Nothing checks who is viewing. SpotRecord.tsx:212 shows InatContext on the same page as the Creek check button to /check (:148), and CityView.tsx:264 shows it to anyone. UPDATE_29 section 8 says "never before the invasive plant question is answered", and the comment at inaturalist.ts:6-7 claims "so they cannot lead anyone's answer". It does nothing today: content/regions/california-bay-area.yaml:7 has invasive_plants: [], and a live GET of /api/inaturalist/strawberry-creek returns "shown":false,"status":"none".
- **Outcome:** fixed. Commit 22c24e6, the smallest fix as instructed. These now say the gate is per creek, not per person, and opens once any finished check on that creek has answered the plant question, a later volunteer included: the comments in worker/src/inaturalist.ts and the Python twin apps/api/inaturalist.py, ADR 0011 (its Decision plus a new Consequences bullet), the README row, and the comments in InatContext.tsx and two test files. The choice, with the per-browser gate left open, is logged in docs/DECISIONS.md. docs/REPORT.pdf and results/report_pdf.json were rebuilt, because the report quotes that README row.
- **Proof:** Two tests. (1) A new e2e case in worker/test/e2e.mjs: one finished check at the bridge spot, then a GET with no token and no check of its own gets shown:true and the sightings. (2) scripts/tests/test_inaturalist.py::test_the_words_say_the_gate_is_per_creek_not_per_person keeps the old promise out of the Worker, the Python module, the ADR and the README. Mutations: putting "so they cannot lead anyone's answer" back into the Worker comment turned the doc test red. Putting the README's "never before the invasive plant question is answered" back turned it red. Making invasiveAnswered skip the newest finished check (results.slice(0, -1)) made the e2e fail with "one finished answer on the creek opens it for every viewer" (actual false).

### R08. The iNaturalist job sends each spot's position to iNaturalist, and the privacy docs do not say so

- **Rank:** should fix (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `scripts/cache_inaturalist.py:180`
- **Evidence:** locations_in_bundle (:136) reads each spot's Location position from our FHIR, which the Worker writes at 5 decimals for a placed pin (worker/src/core/fhir_emit.ts:184 `const digits = spot.coarse ? 2 : 5`). query() then puts "lat": loc.latitude and "lng" into every request to https://api.inaturalist.org/v1/observations. DATA_HANDLING.md:33-35 describes only the cached summary, and I found no mention of positions sent to iNaturalist or Open-Meteo in DATA_HANDLING, the privacy strings, SECURITY.md or THREAT_MODEL.md. REVIEW_02 F29 (Open-Meteo gets 4 decimals and nothing says so) is still true. This does not happen today: with an empty approved list the job asks nothing (:330).
- **Outcome:** fixed. bbef994: `docs/DATA_HANDLING.md` names Open-Meteo (4 decimals) and iNaturalist (the stored precision of a spot, from the daily job) as the two services that get a spot's position, and nothing else.

### R09. Cloudflare failure reports still go to a.nel.cloudflare.com, and for a panel visit they can carry the panel link (REVIEW_02 F33, still true)

- **Rank:** should fix (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `docs/DATA_HANDLING.md:56`
- **Evidence:** The live GET of /t returns report-to {"group":"cf-nel",..."url":"https://a.nel.cloudflare.com/report/v4?..."} and nel {"report_to":"cf-nel","success_fraction":0.0,...}. grep for NEL in docs/DATA_HANDLING.md returns nothing. Under the NEL spec, a failure report names the URL of the request that failed, which for a panel participant is the full link with any panel id.
- **Outcome:** fixed. bbef994: `docs/DATA_HANDLING.md` names Cloudflare's Network Error Logging to a.nel.cloudflare.com and what a report holds.

### R10. The privacy page still says no free text is stored, but typed spot names are stored and shown (REVIEW_02 F104, still true)

- **Rank:** should fix (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `apps/web/components/LocationStep.tsx:123`
- **Evidence:** A live GET of /privacy, under "What we never store": "Free text of any kind. Every answer is a choice from a list or a number." DATA_HANDLING.md:46 says the same. But LocationStep.tsx:123 has `<input className="text-input" type="text" ... name="spot_name" ... maxLength={80} />`, and worker/src/check.ts:210 plainPlaceName accepts and stores it. Patch 11 was not applied.
- **Outcome:** fixed. bbef994: the privacy page and DATA_HANDLING say the one free text kept is a new spot's typed name, which is public.

### R11. JUDGE_QA says the audit log is on no blockchain and lists entries it does not have, with no word on the new OpenTimestamps stamp

- **Rank:** should fix (lens: rules, privacy and security). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `docs/submission/JUDGE_QA.md:97`
- **Evidence:** JUDGE_QA.md:97: "It records the plan tag, the key freeze, the wipe, the lock and record writes. No tokens, no consensus, no ledger shared with anyone." wc -l audit/log.jsonl gives 3, with kinds key_frozen, launch_wipe and plan_tagged only. Since 2026-09-24 the last hash is stamped with OpenTimestamps into Bitcoin (proofs/audit-head-2026-09-24.ots, README.md:154), and the answer, written 2026-09-23 (git blame 8cdc5d2d), does not say so.
- **Outcome:** fixed. bbef994: `docs/submission/JUDGE_QA.md` lists what the audit log records today and says its last hash is stamped daily with OpenTimestamps, a public timestamp service, not a chain of ours.

### R12. Worker JPEG cut still keeps GPS, while README, WRITEUP and Devpost say uploads are stripped

- **Rank:** breaks a hard rule (lens: claims against code and results). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `worker/src/uploads.ts:30`
- **Evidence:** REVIEW_02 F01 is still true at 3fa942f. I copied stripJpeg (worker/src/uploads.ts:30-54) unchanged into scratch and ran it with node 26 on three test files. Output: "plain -> GPS removed", "stray byte before APP1 -> GPS KEPT", "second image after EOI -> GPS KEPT". The loop breaks on the first byte that is not 0xff and copies everything after the first SOS as it is. The judge-facing text says the job is done: README.md:385 "EXIF stripped from uploads", README.md:492 "We never keep ... photo metadata", WRITEUP.md:206 "cuts the metadata segments out of the file" (its proof, e2e.mjs:289-301, only tests the plain shape), docs/devpost.md:81 "EXIF stripped from uploads". Only docs/THREAT_MODEL.md:45 admits "The fix is written and not yet applied".
- **Outcome:** fixed. bbef994: `worker/src/uploads.ts` walks every scan, drops everything after the end marker, allows fill bytes and refuses a JPEG it cannot walk. Production KV held no uploads, so none needed deleting. The threat model row now reads yes; WRITEUP says what changed and when.
- **Proof:** `worker/test/golden.test.ts`, two tests with five probe files; the old cut makes both fail, and turning off the walk through the scan data makes the first fail.

### R13. Threat model proves the gate stops direction tricks with a test marked as an expected failure

- **Rank:** should fix (lens: claims against code and results). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `docs/THREAT_MODEL.md:76`
- **Evidence:** THREAT_MODEL.md:76 marks "Send markup, control characters or text direction tricks to a person" as stopped ("yes") and cites core/tests/test_harden_gate_properties.py::test_a_note_with_any_unicode_direction_control_is_dropped. pytest -rx reports "XFAIL ... bug: BIDI_CONTROLS lacks U+061C ARABIC LETTER MARK, so it reaches a person". I called parse_flags directly with the committed pass table: '\x7f' kept, '\x9b' kept, '؜' kept, '‮' dropped. core/gate.py:141 only blocks ord<32, and BIDI_CONTROLS (gate.py:113-125) has no 0x061C. The same false claim appears in MODEL_CARD.md:146 ("The gate refuses markup, control characters"), MODEL_CARD.md:187 ("every Unicode direction control") and WRITEUP.md:20. 11 of the 1906 collected tests are strict xfails that prove open bugs (pytest --collect-only -m xfail). No judge-facing doc mentions them. These are REVIEW_02 T07 to T09, still open. Mitigation: on today's checker path, core/checker.py:54 clean_note turns every Unicode C category character into a space before the gate sees it.
- **Outcome:** fixed. Commit 993344b. In core/gate.py, _read_note now refuses every unicodedata Cc character with the existing reason, and U+061C is added to BIDI_CONTROLS. After the direction check, any other Cf character is refused with the new reason "note has invisible format characters". Both xfail markers are removed and both tests pass. The reason table in core/tests/test_gate_reasons.py gets six new cases. The THREAT_MODEL row now cites passing tests and says what reached the output before; MODEL_CARD also cites the direction test. make reproduce still matches every committed number. I re-ran make mutation on the new gate: 226 of 229 caught, 98.7 percent. results/mutation.json, the README numbers and the report were rebuilt.
- **Proof:** core/tests/test_harden_gate_properties.py::test_a_note_with_any_control_character_is_dropped, ::test_a_note_with_any_unicode_direction_control_is_dropped, and core/tests/test_gate_reasons.py::test_each_drop_says_why_in_the_same_words. Mutations: (1) setting the Cc check back to ord(ch) < 32 made the control-character test and two reason cases red. (2) Removing 0x061C from BIDI_CONTROLS made the U+061C reason case red. (3) Removing the Cf check made the two format-character reason cases red. (4) Removing both 0x061C and the Cf check made the direction test red with ['U+061C'].

### R14. Mutation score covers four modules, and the checker and rain modules score under the stated bar

- **Rank:** should fix (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:55`
- **Evidence:** The committed numbers are real. I ran make mutation on a git archive copy of 3fa942f in scratch and got exactly 216/219, 319/324, 53/53 and 1477/1543. None of the four modules changed after ac43cd7. But README.md:55 calls these "the code that decides" and says "each must catch 85.0 percent or more". pyproject.toml:67 only_mutate lists gate, followups, scoring and fhir_emit. I kept the same harness and the same core/tests selection and pointed it at the other deciding modules: "core/checker.py: 223 of 288 changes caught ... 77.4 percent", "core/rainfall.py: 181 of 222 ... 81.5 percent", labels 86.7, act 90.0, lock 100.0. The script then printed "mutation: core/checker.py: 77.4 percent of changes caught, under 85". One survivor, checker x_force_answer mutmut_33, changes the malformed flag from True to False for an answer that is not yes, no or cant_tell. That contradicts MODEL_CARD.md "Anything else becomes can't tell and counts as malformed". README steps 2, 3 and 5 name checker.py and rainfall.py as part of the decision path. The TypeScript ports in worker/src/core, which the live site runs, have no mutation run.
- **Outcome:** fixed. Commit 7fb4d26. The README row now reads "four modules, the gate, the follow-up selector, scoring and the FHIR emitter, caught by core's tests ... ; core/checker.py, core/rainfall.py and the Worker's TypeScript ports are not in this run". No module was added. The scripts/mutation.py docstring was reworded to match. The report was rebuilt.
- **Proof:** scripts/tests/test_mutation.py::test_the_readme_names_the_four_modules_the_run_changes_and_no_more ties the row to MODULES. Mutations: putting "the code that decides" back into the row turned it red. Adding core/checker.py to MODULES turned it red (set mismatch).

### R15. README, model card and acceptance cite test_labels.py as proof that health sentences are approved

- **Rank:** should fix (lens: claims against code and results). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `README.md:169`
- **Evidence:** README.md:169 ("State a risk for a named site"), docs/MODEL_CARD.md:55 ("Say anything about health or risk") and docs/ACCEPTANCE.md:60 all name core/tests/test_labels.py. That file tests the observer score label: its tests are test_pass_mark_is_three_of_four, test_fresh_score_reads_k_of_total_with_the_test_date, expiry at 90 and 91 days and similar. grep -c for approved or sentence in it gives 0. core/labels.py only formats "k of 4" text. The tests that do check approved sentences are core/tests/test_healthcard.py, core/tests/test_harden_content_loader.py, apps/api/tests/test_city.py and core/tests/test_act.py::test_an_unapproved_sentence_says_nothing_at_all.
- **Outcome:** fixed. bbef994: the README, the model card and the acceptance table cite `core/tests/test_healthcard.py` and `core/tests/test_act.py`.

### R16. Known weaknesses and the report still say one person set every gold label

- **Rank:** should fix (lens: claims against code and results). **Checked:** 1 of 1 skeptic confirmed.
- **Where:** `README.md:567`
- **Evidence:** README.md:567: "One labeller. Every gold label was set by one person". REPORT.pdf page 6 (pypdf text) says the same, and results/key_hash.json one_labeller_note says "One person set every gold label". docs/deviations.md:13 says "the 16 test labels came from the label column of the picks file that Alex wrote with the planner, which is a Claude chat (commit 81e62ed), so they were not set blind to model output". DATA_CARD.md says the same. The models scored against this key are Claude models. REVIEW_02 F88/F99 is only partly fixed: the deviation was logged and README.md:584 was reworded, but line 567 and the report were not.
- **Outcome:** fixed. bbef994: the README's Known weaknesses says where the key came from and to read accuracy as agreement with it; the report was rebuilt. `results/key_hash.json` keeps its old note, because it was written at the key freeze the audit log records.

### R17. Devpost paste text says the model results have not arrived yet

- **Rank:** should fix (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `docs/devpost.md:79`
- **Evidence:** The "Effective use of data..." paste block says "the same pipeline is ready for 46 frames ... The model results arrive with the paid run." The paid run is done: results/model_pass_table.json has "real": true, and results/cost_log.jsonl holds 5017 paid lines from 2026-09-24T03:04:49Z to 06:05:39Z, 41.106 USD. The file's own header (devpost.md:5) says "The paid model run happened on Sep 23 and 24 ... this text states the pass table only in words". No paste block states the pass table.
- **Outcome:** fixed. bbef994: the Devpost block states the pass table in words, and its character count was recounted.

### R18. Devpost and the README judge path promise a lab record beside ours on /two, and the live route has none

- **Rank:** should fix (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `docs/devpost.md:100`
- **Evidence:** devpost.md:100: "/two: a lab Observation from their sandbox and a volunteer Observation of ours in one viewer." README.md:526 links /two as "lab and volunteer side by side". GET https://second-look-79t.pages.dev/api/two returned 200 with keys ours, theirs, theirs_status, fetched_at, and the values theirs null, theirs_status "down", fetched_at "". README.md:547 and :573 already say it shows ours alone while their sandbox name does not resolve.
- **Outcome:** fixed. bbef994: the Devpost text and the README's judge path say /two shows our record in the lab viewer, with theirs when their name resolves again.

### R19. README says field use never keeps names or free text, but a typed spot name is stored and published

- **Rank:** should fix (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:492`
- **Evidence:** README.md:492: "We never keep names, emails, internet addresses, free text or photo metadata". worker/src/check.ts:214-218 refuses only runs of 5 or more digits, "@" and characters outside a set. check.ts:278 stores spot_name: n.name.trim() and :289 does INSERT INTO spot. docs/THREAT_MODEL.md:44 admits "a person's name typed as a spot name would be stored and shown". Same root as REVIEW_02 F16/F104, still true at 3fa942f.
- **Outcome:** fixed. bbef994: the README says no free text is kept but the typed name of a new spot, which is public.

### R20. Two threat model rows about the live Worker are proved only by Python API tests

- **Rank:** should fix (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `docs/THREAT_MODEL.md:62`
- **Evidence:** THREAT_MODEL.md:4 says it covers "the live site and its Worker". Row :62 (export answers 404 without the token) cites only apps/api/tests/test_study.py. Row :46 (upload deleted after 30 days "on the Worker by the store's own expiry") cites only apps/api/tests/test_upload.py::test_cleanup_deletes_uploads_older_than_thirty_days. The Worker has both routes: index.ts:536-537 for the export token and uploads.ts expirationTtl: KEEP_SECONDS for the expiry. grep -rn for "test/export" or "expiration" under worker/test finds nothing in e2e.mjs or golden.test.ts.
- **Outcome:** fixed. Commit afccdc9. The e2e passes an EXPORT_TOKEN var to wrangler dev. New section "the export": no token, a wrong token and a token one character off each get 404. The right token gets application/zip with sessions.csv and responses.csv, both headers equal to SESSIONS_COLUMNS and RESPONSES_COLUMNS read from apps/api/study.py, and the panel session's rows are in it. New unit test in worker/test/golden.test.ts: storeUpload calls PHOTOS.put with expirationTtl 2592000. The two THREAT_MODEL rows cite both tests. worker/dist/golden.test.mjs was regenerated.
- **Proof:** Mutations: making the export check only that a token is present failed the e2e at "the export" (actual 200, expected 404). KEEP_DAYS = 31 failed the unit test (2678400 vs 2592000).

### R21. README says the AI numbers come from one paid run, and the pass table and headline counts come from different calls

- **Rank:** cosmetic (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:575`
- **Evidence:** README.md:575 says "The AI numbers come from one paid run: four models, three runs each, on 16 photos", README.md:487 says "one paid run on Sep 23 and 24", and REPORT.pdf page 6 repeats it. make reproduce printed "7 paid runs". I recounted per feature from model_sweep_20260924T054756Z (behind the pass table): Fable dug-out 8 of 12, Opus 11 of 12. benchmark_20260924T054939Z (behind README.md:50) has Fable 10 of 12 (did not pass) and Opus 9 of 12 (passed). Totals are sweep 32/35/35/32 against benchmark 31/33/33/34. Every paid call is dated 2026-09-24 in UTC and Sep 23 in Pacific time, so no clock gives "Sep 23 and 24". MODEL_CARD.md does disclose "a second set of calls".
- **Outcome:** fixed. bbef994: the README says the AI numbers come from paid calls on Sep 23, Pacific time: the sweep behind the pass table, a second set behind the right-answer counts, and the footage run.

### R22. README says names that look like a test are refused, but the code keeps them and lists them apart

- **Rank:** cosmetic (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:151`
- **Evidence:** README.md:151: "test-looking names are refused". Neither worker/src/check.ts nor apps/api/check.py calls looks_like_a_test_name. apps/api/city.py:207-210 says "kept out of the numbers and listed separately for a person to look at. It is never deleted." The cited test is named test_a_name_that_reads_like_a_test_is_flagged.
- **Outcome:** fixed. bbef994: the README says names that read like a test are kept out of the counts and listed apart.

### R23. Data card says every author is credited on /credits, but two footage authors are missing

- **Rank:** cosmetic (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `docs/DATA_CARD.md:72`
- **Evidence:** DATA_CARD.md:72: "Every author is credited on /credits and in the manifest." I fetched https://second-look-79t.pages.dev/credits and checked every author in photos/manifest.csv. 15 of 84 rows are missing: v01 frames by senapa (6) and v06 frames by OkState Ag (9), both CC BY 3.0. apps/web/scripts/build-content.mjs:24 says "Benchmark photos stay on the server side". README.md:611 has the scope right ("every one a visitor can see").
- **Outcome:** fixed. bbef994: the data card says every author of a photo a visitor sees is on /credits, and every author is in the manifest.

### R24. Model card says every model answered cant tell on the drawn frames, but only majority answers were kept

- **Rank:** cosmetic (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `docs/MODEL_CARD.md:105`
- **Evidence:** MODEL_CARD.md:105 says the four drawn frames "got can't tell from every model on every feature". make reproduce printed: "the run kept only each model's majority answer on the adversarial frames, so those answers are as recorded; the cost of their 192 calls is regraded". That is 192 calls, 3 per model per frame and feature, and single answers were not kept.
- **Outcome:** fixed. bbef994: the model card says each model's majority answer over three runs was can't tell, and that the run kept majority answers.

### R25. The 20 second return check is a number with no results file

- **Rank:** cosmetic (lens: claims against code and results). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:444`
- **Evidence:** README.md:444 "the 20 second return check", also docs/API.md:40 and docs/ARCHITECTURE.md:11. No file in results/ times the quick check: grep for quick in results/ finds only api_inventory, screens and test_counts. Hard rule 12 says every number in README or docs comes from results/. Design constants such as 16 photos or 30 days are specifications, but this one is a measured-sounding duration.
- **Outcome:** fixed. bbef994: "the 20 second return check" is "the three-question return check" in the README, API and architecture docs.

### R26. The credits page scrolls sideways on a phone and squeezes author names to one word per line

- **Rank:** breaks a hard rule (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `apps/web/app/credits/page.tsx:101`
- **Evidence:** GET-only Playwright on https://second-look-79t.pages.dev/credits: at 390 px wide, documentElement.scrollWidth is 713; at 320 px it is also 713. The widest element is the footage link "Evaluating Stream Restoration in the Oregon Coast Range: Karnowsky Creek in 2026" (right edge 713), inside SPAN.row-end. apps/web/app/globals.css:507-508 gives .row-end "flex: none", and credits/page.tsx:101-105 puts the footage title in that end slot, so it cannot wrap. Screenshot: the title runs off screen and "Stravaiging with Andy" is stacked one word per line. The other 17 pages I measured fit at 390 and 320. /accessibility promises "Every screen fits a narrow phone without sideways scrolling" (en.json:285). apps/web/tests/reflow.spec.ts checks 7 routes and /credits is not one. This fails WCAG 2.2 SC 1.4.10 Reflow, so it breaks rule 17.
- **Outcome:** fixed. 022ece3: apps/web/app/credits/page.tsx puts the footage and video titles in the row value (title link, line break, licence), which wraps, instead of the end slot. The .row-end CSS is left alone, so the score screen's gauges do not change. reflow.spec.ts measures against the viewport width and covers 11 routes. Added a line to deviations.md.
- **Proof:** reflow.spec.ts '/credits fits the phone width' (a probe after the fix: 390 at 390 and 320 at 320). Mutation: put the bbef994 credits page back and rebuilt. The test went red, 714 > 390. Restored, and it passed.

### R27. The README says the city page shows OneAquaHealth measures but the live page and its screenshot show none

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:561`
- **Evidence:** README:561, See it work: "What the city then saw | What the creek needs, in OneAquaHealth's own restoration measures ... each with its source | /city?creek=strawberry-creek, docs/screens/city.webp". README:103 gives the alt text "what volunteers found there and what OneAquaHealth says to do". Live GET /api/city/strawberry-creek returns visits 0, spots 0, needs [], and the page reads "0 visits at 0 spots", "No measure is shown yet" and "Nobody has checked this creek yet." results/screens.json has a different alt for the same file: "before anyone has checked it: no visits yet, and no OneAquaHealth measure shown yet". The image shows the empty state. This is the only README alt that differs from screens.json. The 45 second path (README:526) also sends judges here for "what the city sees". make demo-offline does show 3 visits, 3 measures and 1 pipe; I ran it on spare ports.
- **Outcome:** fixed. e8f439f: scripts/verify_claims.py gains alt_problems(): every <img> whose src has a row in results/screens.json must carry that row's alt word for word (HTML entities unescaped; a missing alt fails too). The last line now reads 'verify-claims: 85 claim(s), 34 alt text(s) checked, all match results/'. Five tests in scripts/tests/test_verify_claims.py, including one on the committed README.
- **Proof:** With the old city alt put back into README.md, 'uv run python scripts/verify_claims.py --synthetic' printed 'alt text drifted: docs/screens/city.webp ...' and exited 1. Mutation: changed the comparison to 'elif False and html.unescape(...) != alts[src]'; test_an_image_alt_that_differs_from_the_gallery_fails went red; restored, 14 passed.

### R28. The empty city notice blames approval when the list is empty because nobody reported anything

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `apps/web/components/CityView.tsx:185`
- **Evidence:** CityView.tsx:185 shows city.needs_waiting whenever view.needs.length === 0. That text (en.json:444) says "an empty list here means nobody has approved one, not that the creek needs nothing." The component ignores the API field measures_waiting_for_approval, which is false on live. The measures are approved: after a walk, /city?walk=v02 shows "Find and fix leaking or wrongly connected sewers..." with "OneAquaHealth Policy Brief (2026), page 9", and make demo-offline shows three measures.
- **Outcome:** fixed. a1a243c: CityView shows city.needs_waiting only when view.measures_waiting_for_approval is true. Otherwise it shows the new key city.needs_none, 'No measure applies to what people have reported here so far.' Changes en.json, the worker content, the sw.js version and deviations.md.
- **Proof:** record.spec.ts '/city with no measure to show, measures approved' and '... not yet approved' (both cases). Mutation: the condition reverted to `view.needs.length === 0 ?`. The approved case went red (text not found) while the not-yet-approved case stayed green. Restored, and it passed.

### R29. Every creek check question carries a Draft wording badge while the README says the check mirrors the official app

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/form.yaml:29`
- **Evidence:** content/form.yaml has 24 items and 0 with verified_against_app true (counted with yaml.safe_load; the only "true" is in the header comment). I drove /walk/v02 to the end with GET only: 24 questions, each rendered with "Draft wording" (FormQuestion.tsx:56). /check says "We have not yet checked the questions marked draft against that app." README:175 says "The creek check asks the official app's questions", README:414 says "The creek check mirrors the official Citizen Science App's items in their order", and README:418 says the same. JUDGE_SIM_00 also noticed this; REVIEW_02 did not raise it.
- **Outcome:** fixed. bbef994: the README says the creek check mirrors the app's items in order, each marked draft wording until checked against the app itself.

### R30. The how we know page says the plan is not yet tagged but the tag exists and the verify page says so

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `apps/web/app/how-we-know/page.tsx:6`
- **Evidence:** The live /how-we-know page says "Analysis plan tag: prereg-v1 (not yet tagged)." The live /verify page says "The analysis plan was tagged. Written at (UTC) 2026-09-22T05:36:06Z". git for-each-ref refs/tags/prereg-v1 gives "tag 2026-09-21 22:35:40 -0700". page.tsx:6 falls back to "prereg-v1 (not yet tagged)" when NEXT_PUBLIC_PLAN_TAG is unset. Nothing sets that variable; the only other place it appears is DEPLOY.md:200, with the same default. REVIEW_02 F78 was about analysis_plan.md line 3, not this public page.
- **Outcome:** fixed. 1de5fef: the fallback is now 'prereg-v1', with a comment saying why. The DEPLOY.md:200 default says the same. Added a line to deviations.md.
- **Proof:** landing.spec.ts 'the how we know page names the plan's tag as made' (checks the text and that 'not yet tagged' is absent). Mutation: the fallback put back to 'prereg-v1 (not yet tagged)' and rebuilt. The test went red. Restored, and it passed.

### R31. The walk record badge says this record passed validation but it shows the CI run on other files

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `apps/web/components/FhirView.tsx:47`
- **Evidence:** At the end of /walk/v02, View as FHIR shows "Validated against guide commit b907cf0: passed" over a Bundle made on the phone (id sl-visit-walk-407f1ef7f46eaa42, timestamp 2026-09-24T09:40:29Z). The only request was GET /api/fhir/validation. It returns ran_at_utc 2026-09-24T03:30:19 and files_validated 14, a fixed list of repo files, and this record is not among them. FhirView.tsx:47-51 prints that verdict for any record. On the same screen, "Copy the curl line" copies "This record was made on your phone and has no web address." (WalkFlow.tsx:163, en.json:509).
- **Outcome:** fixed. 0e512b8 (shared with R41 and R42 through WalkFlow.tsx and walk.spec.ts): FhirView takes `curl: string | null`. When curl is null (a phone record), the badge reads walk.validated_like, 'Walk records made the same way passed the HL7 validator on {date}. This one was made on your phone and was not checked.' It shows only when errors is 0 and walk_records_validated is above 0. The curl label and the copy button are replaced by the no-address sentence. WalkFlow passes curl={null}. FhirValidationOut gains walk_records_validated, and the mock validation gains files_validated 14 and walk_records_validated 2. The session then worded the /spot badge the same way: records built by the same code passed the validator in CI.
- **Proof:** walk.spec.ts end-screen assertions: data-testid fhir-badge has the new text, 'Validated against guide commit' is absent, and there is no 'Copy the curl line' button. Mutation: the phone branch's condition changed to `curl === "mutated-never"`, so phone records get the server badge again. The test went red with 'Received: "Validated against guide commit b907cf0: passed"'. Restored, and it passed.

### R32. The demo city counts one walk as two checks for pipes, so REVIEW_02 F82 is still true and now visible

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `core/act.py:163`
- **Evidence:** I did one walk on /walk/v02, answering Yes to both pipe questions (draining_pipes, sewage_discharge), then pressed "See this creek as a city would". /city?walk=v02 shows "Checks from this phone: 1" and "Pipes and drain outlets / Checks that saw it: 2". WalkCity.tsx:44 renders f.visit_ids.length, and core/act.py:163 appends the visit id once per answer. REVIEW_02 F82 ranked this cosmetic because "/city never shows two". This screen does.
- **Outcome:** fixed. Commit 5d97360. core/act.py and worker/src/core/act.ts now add a visit id to a finding only once. New golden vector "one visit answering both pipe items is one visit" in evals/golden_vectors.py, which regenerated worker/golden/act.json (only the new case changed). New core test. Deviation logged.
- **Proof:** core/tests/test_act.py::test_one_visit_answering_both_pipe_items_is_one_visit, plus the golden vector run by npm test and evals/golden_vectors.py --check. Mutations: restoring the unconditional push in act.ts made npm test red (visit_ids [v14, v14]). Restoring the unconditional append in act.py made the core test red (('v1','v1','v2')) and made golden_vectors --check fail.

### R33. The two page shows the hand-made golden visit as a real volunteer answer with no example label

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `worker/src/two.ts:35`
- **Evidence:** two.ts:35 falls back to fhir/golden/visit-strawberry-creek-1.json when D1 has no visit. Live GET /api/two: ours.id is sl-obs-visit-0001-bank-type, effectiveDateTime is 2026-09-24T16:40:00Z (seven hours after my GET at 09:31Z), there is no meta.tag, and golden file line 408 has the same time. The page reads "a volunteer answer from Strawberry Creek ... When Sep 24, 2026, 9:40 AM ... Where Location/sl-loc-spot-1 ... Observer score 4 of 4 on this feature, tested Sep 23, 2026", and the word example appears nowhere. README:484 lists this visit as "example, hand shaped", and /city says "Nobody has checked this creek yet."
- **Outcome:** fixed. Commit 9bdd7b2. The Worker's two() and the Python twin now return ours_example (true when no visit is stored and the golden visit is shown) and ours_place (the Location's name, read from the same Bundle). On the page, RecordCard takes place and note props. TwoObservers shows "Example record, made by hand for this demo. No volunteer has sent a creek check yet." on the volunteer card, uses an example intro, and shows the place by name. Two locale strings were added and worker/src/content.json rebuilt, so content_hash becomes 3436a125a9e7df63 and sw.js follows. CONTRACTS.md and API.md were updated. Deviation logged.
- **Proof:** Three tests. (1) Worker e2e "an empty store": ours_example true and ours_place "Strawberry Creek, campus reach, spot 1"; in "two observers", ours_example is false once visits exist. (2) apps/api/tests/test_fhir_routes.py asserts both fields. (3) The Playwright test "/two labels the hand-made golden visit as an example and names its place" in apps/web/tests/record.spec.ts, run on port 3161 with a temporary config that was not committed. Mutations: example forced to false failed the e2e ("the golden visit is labelled an example"). place forced to null failed the e2e. Dropping the note in TwoObservers failed Playwright. Showing refText in place of place failed Playwright. Forcing example = False in fhir_routes.py failed pytest.

### R34. The judges page promises the same creek beside a lab result but the lab record is from another place

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/locales/en.json:419`
- **Evidence:** en.json:419 has "judges.two": "The same creek beside a laboratory result". worker/src/two.ts:15 fixes the lab side to "Location/Loc-Almyros", and the TwoObservers.tsx comment says "the live pair is a lab reading from another place". Today live /two shows "Their sandbox did not answer, so only our record is shown." and /api/two returns theirs null, theirs_status "down".
- **Outcome:** fixed. a8fdd46: judges.two in en.json now reads 'A volunteer record in the viewer built for laboratory results'. Regenerated the worker content and the sw.js version. Added a line to deviations.md.
- **Proof:** record.spec.ts "the judges' door names /two for what it shows" (new label links to /two, old label absent). Mutation: en.json judges.two put back to the old words and rebuilt. The test went red (link not found). Restored, and it passed.

### R35. The README says the walk footage comes from Wikimedia Commons but all three walks come from YouTube

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:589`
- **Evidence:** README:589 says "The creek footage in the video and the walks comes from Wikimedia Commons". content/walks.yaml:8, :34 and :60 have source_url youtube.com/watch?v=vN5ArGGmdUY, 7soch86PJ2U and DaD3RJGEvhM. The live /walk/v02 "Source" link goes to YouTube. Live /credits says "The video walks and their stills are cut from these openly licensed videos" and lists the three YouTube links.
- **Outcome:** fixed. bbef994: the README says the video's footage is from Wikimedia Commons and the three walks are cut from CC BY 3.0 videos on YouTube.

### R36. The consent screen says the test takes about four minutes while the README and landing say two

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/locales/en.json:9`
- **Evidence:** The live /t?src=other page, the first screen behind the README's main button, says "This is a usability test of a training tool. It takes about four minutes." The landing page says "Find out in two minutes", /judges says "Take the two minute test", and the README says "a two-minute photo test" (line 1) and "Take the two-minute test" (lines 22 and 35).
- **Outcome:** fixed. bbef994: the README says the two-minute test takes about four minutes with its lesson, as the consent says. The landing page's words are part of the frozen test flow and stay.

### R37. The README 45 second judge path takes several minutes

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:526`
- **Evidence:** README:526 says "A 45 second path: the test, a creek from your desk, a record made on your phone, ...". The consent says the test takes "about four minutes". The record link, /walk/v02, is a 40 second clip (walks.yaml:15, seconds: 40) followed by 24 questions; my run reached "Question 24 of 24". /judges calls it "a one-minute video walk".
- **Outcome:** fixed. bbef994: the README's judge path says about ten minutes, and that the walk is a 40 second clip and the full 24 question check.

### R38. Consent still says Nothing else although the session stores the link source, so REVIEW_02 F31 is still true

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/locales/en.json:10`
- **Evidence:** Live consent text: "We store: a random session id, which group you were in, your answers, how long each screen took, a hashed random browser token, your device type and the version of this text. Nothing else." The README's own button links to /t?src=other. worker/src/index.ts:143 and :160 store source_label. Live /privacy lists "A coarse label from the link you used: poster, chat, friends, creek group or other."
- **Outcome:** fixed. bbef994: the consent's list of what is stored names the kind of link you came from; logged in `docs/deviations.md` with the consent version change.

### R39. The city, record, judge mode and quick check pages have no title of their own

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `apps/web/app/layout.tsx:10`
- **Evidence:** Live document.title for /city?creek=strawberry-creek, /spot, /demo and /quick is "Second Look", the same as the home page. Other pages have their own, such as "For judges: Second Look" and "Photo credits: Second Look". apps/web/app/city, spot, demo and quick page.tsx files export no metadata; only layout.tsx:10 sets the site name. This is arguably a WCAG 2.4.2 Page Titled miss (rule 17). I rank it should fix because a site name alone is sometimes accepted.
- **Outcome:** fixed. cc2d208: new apps/web/app/{city,spot,demo,quick}/layout.tsx. Each exports metadata titled '<page title key>: Second Look' and returns its children. The pages stay client components. Added a line to deviations.md.
- **Proof:** landing.spec.ts '<path> has a title of its own', four tests. Mutation: deleted the four layout files and rebuilt. All four went red with 'Received: "Second Look"'. Restored, and they passed.

### R40. The accessibility page promises 48 pixel links but the judges page links are 24 pixels tall

- **Rank:** should fix (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/locales/en.json:286`
- **Evidence:** en.json:286 says "Buttons and links are at least 48 pixels tall, so they are easy to tap." GET-only Playwright at 390 px measured these heights on /judges: "Take the two minute test" 24, "Creek check" 24, "Check a creek from your desk" 24, "For a city" 24, "Photo credits" 24. On /credits, 107 links are under 48 px ("Source" 27, licence links 20). judge-check's design check reports only "tap targets 2 passed".
- **Outcome:** fixed. 6a87751: the /judges row links get className row-link. globals.css .row-link is display inline-flex, align-items center, min-height var(--tap), which is 48px. The words did not change and the sentence was not softened. Added a line to deviations.md. The /accessibility sentence now says buttons and the /judges links are at least 48 pixels, and a link inside a sentence or a list of credits is the height of its text.
- **Proof:** design.spec.ts "tap targets: every link on the judges' door is at least 48 pixels tall". It runs in make design-check, which now reports 'tap targets 3 passed'. Mutation: removed min-height from .row-link and rebuilt. The test went red, listing 8 links under 48. Restored, and it passed.

### R41. The walk list says A creek in United Kingdom and A creek in United States

- **Rank:** cosmetic (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/walks.yaml:36`
- **Evidence:** Live /walk shows "A creek in Russia", "A creek in United Kingdom" and "A creek in United States". walks.yaml:36 and :62 set creek_name that way.
- **Outcome:** fixed. 0e512b8: build_walks.creek_name(country) adds 'the' for names like United..., ...Kingdom/States/Republic/Islands, Netherlands and Philippines. The builder uses it. walks.yaml's two creek_name lines now say what the rule writes: the script needs the video cache to rerun, so the lines were edited, and a test holds them to the rule. The walk list, the walk heading, the walk page title and the clip label use walk.creek_name. The unused walk.title key is removed, and walk.clip_label is now '{creek}, a short clip with no sound'.
- **Proof:** test_build_walks.py::test_a_creek_name_reads_with_the_where_the_country_takes_it and ::test_the_committed_walks_carry_the_creek_name_the_rule_writes, plus walk.spec.ts (links named by creek_name; no link text matches /in United/). Mutations: (1) walks.yaml put back to 'A creek in United Kingdom/States' and rebuilt. The Playwright test went red (4 bad names received) and the yaml test went red. (2) creek_name made to return f"A creek in {country}". Both Python tests went red. Restored, and all passed.

### R42. The walk progress count changes its total halfway through

- **Rank:** cosmetic (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/locales/en.json:112`
- **Evidence:** Driving /walk/v02: "Question 20 of 23" is followed by "Question 21 of 24" once the plant follow-up "Which ones?" appears. That screen also says "No plant list for this region yet. Pick Can't tell."
- **Outcome:** fixed. 0e512b8: lib/content.ts questionCount(shown, index) counts only items without depends_on, and total is the count of those. A follow-up shares its parent's number. Used in WalkFlow and CheckFlow. After the fix the probe read 20 of 23, 20 of 23, 21 of 23.
- **Proof:** walk.spec.ts collects every 'Question n of m' while driving a walk, asserts 'Which ones?' appeared, and asserts one distinct total. Mutation: questionCount returned n: index + 1 and total: shown.length (the old count), rebuilt. The test went red, 'Expected: 1, Received: 2' distinct totals. Restored, and it passed.

### R43. The record page fetches an empty spot id on every load and logs a 404

- **Rank:** cosmetic (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `apps/web/app/spot/page.tsx:9`
- **Evidence:** Live /spot?id=example sends GET /api/spot/ (404) and then GET /api/spot/example (404), and the console shows two "Failed to load resource ... 404" errors. useQueryParam's server snapshot is "" (QueryParam.tsx), and SpotRecord's effect fires with it. /spot with no id says "No record for this spot." instead of saying no id was given.
- **Outcome:** fixed. 65cde9c: QueryParam.tsx gains useQueryParamOrNull, whose server snapshot is null. spot/page.tsx shows the loading line while the id is null and the new spot.no_id 'This link names no spot.' when it is empty. It renders SpotRecord only for a real id. Updated en.json, the worker content, the sw.js version and deviations.md.
- **Proof:** record.spec.ts '/spot asks only for the id in the link, and says when the link names none'. It asserts the spot requests equal ["/api/spot/example"] after /spot?id=example and again after /spot, and it checks the message. Mutation: spot/page.tsx put back to the base version (useQueryParam straight into SpotRecord) and rebuilt. The test went red, with '/api/spot/' as an extra received request. Restored, and it passed.

### R44. The judge mode heading says Sep 28 while its body says Sep 27

- **Rank:** cosmetic (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/locales/en.json:410`
- **Evidence:** Live /demo shows the heading "Judge mode opens on Sep 28" and the body "It opens when the data locks, on Sunday Sep 27 at 18:00 PDT." Both are 2026-09-28T01:00Z (Sep 27 is a Sunday), but a judge reads two dates. With the browser clock set to 2026-09-29, the page opens to "Photo 1 of 16" as promised.
- **Outcome:** fixed. 7e3d758: demo.shut_body now ends 'It opens when the data locks: Sep 28 at 01:00 UTC, which is Sunday Sep 27 at 18:00 PDT.' The heading stays as it was, as do the Worker's 403 text and live-readonly.mjs. Updated the worker content, the sw.js version, and a deviations line that also notes the content_hash move from this review's locale changes.
- **Proof:** demo.spec.ts 'judge mode is shut before the lock and open after it' asserts the new sentence. Mutation: demo.shut_body put back to the old sentence and rebuilt. The test went red (text not visible). Restored, and it passed.

### R45. The README says there is no recruited study while the site calls the test the study

- **Rank:** cosmetic (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `content/locales/en.json:415`
- **Evidence:** README:68 says "No recruited study. The two-minute test stays live as the volunteer's own calibration step and for judges." Live /judges says "It is the study, so your answers count as a session." /about says "The test is a usability study ... Half the people see the lesson first and half see it after. We publish the result either way." /demo says "while the study is running".
- **Outcome:** fixed. bbef994: the README says the test runs as a pre-registered study that stays open, and that a paid panel may add sessions before the lock.

### R46. The README says every door is on the judges page but four are missing

- **Rank:** cosmetic (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `README.md:526`
- **Evidence:** README:526 says "Every door is on /judges." Live /judges links /demo, /t?src=other, /check, /walk, /walk/v02, /two, /city, /how-we-know, /verify and /credits. It has no link to /quick, /poster, /privacy or /accessibility, which README:547 and the gallery list.
- **Outcome:** fixed. bbef994: the README says the main doors are on /judges.

### R47. judge-check prints a row of dots instead of the Python test count

- **Rank:** cosmetic (lens: what a judge meets first). **Checked:** reproduced by the fixer before the fix.
- **Where:** `scripts/judge_check.py:112`
- **Evidence:** I ran make judge-check in a fresh clone of 3fa942f. It printed "ok tests: python: .................................. [100%]". judge_check.py:112 adds -q on top of pyproject.toml:57 addopts "-q", which hides pytest's "N passed" line, so the judge never sees the 1906 from README:469.
- **Outcome:** fixed. cfce80e: scripts/judge_check.py step_tests runs 'uv run pytest' with no extra -q. New test test_the_tests_step_shows_how_many_python_tests_passed runs a real pytest with the repo's addopts and the arguments step_tests gives. Under the real suite the line read 'python: 1902 passed, 2 skipped, 11 xfailed in 183.73s'.
- **Proof:** Mutation: put '-q' back in step_tests' argv; the new test failed (line was 'python: . [100%]'); restored, 7 passed.

### R48. Worker tests all pass when panel is dropped from the Worker's source labels

- **Rank:** should fix (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `worker/src/index.ts:33`
- **Evidence:** The live site's API is the Worker, not apps/api. In a scratch copy (git archive 3fa942f) I removed "panel" from `const SOURCE_LABELS` in worker/src/index.ts. Then `npm test` printed "tests 12 ... pass 12 ... fail 0", `npm run typecheck` exited 0, and `E2E_PORT=8931 npm run e2e` printed "worker e2e: 9 sections passed against wrangler dev on port 8931" and exited 0. Searching worker/test and worker/golden finds no "panel" and no "by_source" assertion. Only done_items.check_panel_prep noticed: "worker/src/index.ts does not keep the panel source label", and that is a text regex run by make done-check, not by make check or CI. apps/api/tests/test_panel.py covers the Python API only. A live GET of /api/test/counts shows "panel":0 today, so the label is currently kept. If it were dropped, panel sessions would be stored as "other" and D51 would never pass.
- **Outcome:** fixed. Commit 19df831. New e2e section "counts by source". It first checks that by_source is all zero, including panel. It then finishes one real, non-QA sitting with source_label panel and one with PROLIFIC_PID=abc, and expects by_source.panel == 1, by_source.other == 1 and 2 completed sittings.
- **Proof:** Mutation: dropping "panel" from SOURCE_LABELS failed the e2e at "counts by source" (by_source had no panel key).

### R49. A synthetic result flipped to significant passes make check and CI; only make reproduce catches it

- **Rank:** should fix (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `Makefile:34`
- **Evidence:** `check:` (Makefile:34) and .github/workflows/check.yml run no `make reproduce`. The tests call reproduce.paid_checks, synthetic_sweep and synthetic_benchmark. A search finds no test that calls synthetic_checks, synthetic_analyses or synthetic_footage. In a scratch copy I set results/usability_synthetic.json primary.permutation_p from 0.051 to 0.049 and rejects_at_alpha_05 from false to true. The full pytest run then had 15 failures, all from git being absent in the archive copy (test_adr, test_no_video_files, test_commit_problem_uses_git_ancestry), and none mentioned the file. `make verify-claims` printed "all match results/". `python evals/reproduce.py` printed "FAIL results/usability_synthetic.json ... /primary/permutation_p: committed 0.049, regraded 0.051 ... /primary/rejects_at_alpha_05: committed True, regraded False". make reproduce takes 32 s here.
- **Outcome:** fixed. a7da329: .github/workflows/check.yml runs '- run: make reproduce' right after '- run: make check' (not added to make check). New test evals/tests/test_reproduce.py::test_ci_runs_make_reproduce_after_make_check reads the workflow with yaml and the Makefile recipe.
- **Proof:** Mutation: deleted the make reproduce step from check.yml; the test failed with the list of run steps; restored, it passed. The flip itself fails make reproduce (exit 2), which the new CI step runs.

### R50. CI retries each web test once, so a test that fails and then passes counts as green

- **Rank:** should fix (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `apps/web/playwright.config.ts:13`
- **Evidence:** The config has `retries: process.env.CI ? 1 : 0`. GitHub Actions sets CI, and check.yml runs `make e2e`, which covers verify.spec.ts, panel.spec.ts, inaturalist.spec.ts and every other web spec. In scratch I installed @playwright/test 1.63.0, the version in apps/web/package-lock.json, with the same retries line and a test that fails on its first try only (`expect(info.retry).toBe(1)`). `CI=1 npx playwright test` printed "1 flaky" and exited 0. Without CI it printed "1 failed" and exited 1.
- **Outcome:** fixed. c98ed22: apps/web/playwright.config.ts adds failOnFlakyTests: !!process.env.CI and keeps the one CI retry, so the report still shows flaky versus broken. 7397af7: the DEPLOY.md CI row says so (and adds the PW_REUSE row that test_deploy_config requires).
- **Proof:** Mutation: failOnFlakyTests: false; test_in_ci_a_test_that_passes_only_on_its_retry_fails_the_run went red; restored, 6 passed. test_outside_ci_there_is_no_retry pins the no-CI behaviour ('1 failed').

### R51. The 16 newest done items have no test, and two pass with the thing they check missing

- **Rank:** should fix (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `scripts/done_items.py:1649`
- **Evidence:** scripts/tests/test_done_items.py calls 37 of the 53 CHECKS. None of these 16 is called: panel-prep, panel-analysis, human-row, contributed-back, ots, verify-page, reproduce, mutation, lighthouse-landing, model-card, threat-model, report-pdf, data-card, second-labeller, inaturalist, rerun-after-update. Scratch proofs: (1) I deleted apps/web/components/InatContext.tsx and replaced every inat* word in the other components. `done_items.py inaturalist` still printed "done-item inaturalist: ok", because `"inat" not in web.lower()` matches "coordinates" in LocationStep.tsx:13. (2) I replaced scripts/install_anchor_job.sh with a script that holds only "# robots only: this job does nothing" and "exit 0". `done_items.py ots` printed "done-item ots: ok", because line 1477's `"ots" not in read(...)` matches "robots". (3) I removed the reproduce step from judge_check.py. check_reproduce_wired still returned [], because the Makefile comment "judge-check:  # its second step is make reproduce" satisfies line 1508. test_judge_check does catch this third case.
- **Outcome:** fixed. 0b65d3b: check_inaturalist needs 'export function InatContext' and '<InatContext' in CityView.tsx and SpotRecord.tsx; check_ots needs scripts/anchor_audit_head.py in the RUN= line and the plist running $RUN; check_reproduce_wired needs the Makefile judge-check recipe to run scripts/judge_check.py, a step_reproduce that runs "reproduce", and a call to it. test_done_items.py gains an update29 tree fixture (git init for rerun-after-update, github_state stubbed), parametrized pass and empty-tree fail tests for all 16, three tests repeating the three mutations, and test_every_check_is_called_by_a_test. 024f6a6: the fixture builds the working notes paths from parts, because test_go_public failed on an f-string path.
- **Proof:** After the fix the three mutations on the real repo printed 'no component shows the iNaturalist context line', 'scripts/install_anchor_job.sh does not anchor the audit head daily' and 'make judge-check does not run make reproduce'. Mutation: restored done_items.py from HEAD (old substring checks); the three new mutation tests went red (3 failed, 161 passed); restored, 164 passed. Harness check: flipping returncode tests in check_panel_analysis and check_rerun_after_29 made their pass-tree tests red, so the pytest subprocess and git really run.

### R52. Worker e2e branches on the real clock for the judge mode lock

- **Rank:** should fix (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `worker/test/e2e.mjs:389`
- **Evidence:** The e2e runs `if (Date.now() < Date.parse("2026-09-28T01:00:00Z")) { assert.equal(demo.status, 403) ... } else { assert.equal(demo.status, 200) }`. Every run so far has taken the 403 branch, so the open-after-lock branch has never run. After Sep 28 the shut branch stops being tested. The web tests use a fake clock instead (demo.spec.ts:22 `page.clock.install({ time: AFTER_LOCK })`). The Worker's own `const DATA_LOCK_UTC = Date.parse("2026-09-28T01:00:00Z")` (index.ts:31) is still not compared with core/lock.py by any test. Only core/tests/test_lock.py checks the Python constant. That part is REVIEW_02 F60 and is still true at 3fa942f.
- **Outcome:** fixed. Commit 62bded7, plus follow-up d5d7f5c. The Worker's demo route reads lockClock(env), which uses E2E_NOW when it is set and the real clock otherwise; this is a new function outside the 16 frozen ones. The e2e starts its main Worker with E2E_NOW one second before the lock (403), then a second short-lived Worker on PORT+2 with E2E_NOW at the lock itself (200, correct true or false, unknown item 404). New scripts/tests/test_worker_lock.py: the Worker's DATA_LOCK_UTC must equal core.lock; no wrangler.jsonc, deploy script or workflow may set E2E_NOW; only index.ts and e2e.mjs under worker/ may name it. DEPLOY.md got the configuration row that test_deploy_config requires, saying it is never set on a deployed Worker. THREAT_MODEL and DECISIONS were updated.
- **Proof:** Mutations: changing < to <= at the lock failed the e2e at "judge mode open at the lock" (403 instead of 200). Making lockClock ignore E2E_NOW failed the same step. Changing the Worker constant to 2026-09-29T01:00:00Z failed test_the_worker_lock_is_the_python_lock.

### R53. The cannot fail guard in done_check accepts common shapes that cannot fail

- **Rank:** cosmetic (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `scripts/done_check.py:60`
- **Evidence:** never_fails() returned None (accepted), and bash exited 0 even though the file is missing, for each of: `test -f missing || test 1`, `test -f missing || [ 1 ]`, `test -f missing; test 1`, `! test -f missing || ! true`, `(test -f missing; true)`, and `grep -q else x; if test -f missing; then false; fi`. In the last one, the word else anywhere turns off the if rule. The docstring at line 26 says "A command that cannot fail is refused when the file is read". No command in docs/internal/DONE.md at 3fa942f uses these shapes today.
- **Outcome:** fixed. 0f73810: scripts/done_check.py NEVER_FAILS now refuses true or : that closes a ( ) or { } ending the command, and a test or [ of one fixed word with no variable. The if rule now counts keyword ifs against keyword elses (else after ; or a newline), so the word else in a grep pattern no longer turns it off, and neither does an else that belongs to a different if. Shapes 1, 2, 3, 5 and 6 plus six variants were added to the refused list. Seven accepted cases were added. The docstring lists the new shapes.
- **Proof:** Mutations, each restored afterwards: KEYWORD_ELSE set to r'\belse\b' made the grep-else shape red. A (?!) prefix on the fixed-word regex made 5 cases red. The old ends-in-true regex made 3 cases red. Restored: 87 passed. The real DONE.md still parses.

### R54. The anchor job's only test is skipped in CI, and the iNaturalist job installer has no test

- **Rank:** cosmetic (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `scripts/tests/test_ots.py:160`
- **Evidence:** The test is marked `@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS only")`, and check.yml has `runs-on: ubuntu-latest`, so CI shows an s and stays green. A search of the tests finds install_anchor_job only in test_ots.py. It finds no test for install_inaturalist_job.sh, install_backup_job.sh, install_cache_job.sh or install_repush_job.sh.
- **Outcome:** fixed. 6ad0227: new scripts/tests/test_install_jobs.py runs each installer with HOME in tmp and stand-in launchctl and uv. It reads the plist with plistlib. Each test has a 'real' case, skipped without plutil, and a 'stand-in' case that puts a fake plutil on PATH and checks it was asked to -lint. It covers install_anchor_job.sh (moved from test_ots.py) and install_inaturalist_job.sh.
- **Proof:** Mutation: swapped the two commands in the anchor RUN line, ran with no plutil on PATH as CI does: 1 failed, 1 passed, 2 skipped. Second mutation: pointed the iNaturalist plist at cache_their_records.py; the stand-in case failed. Both restored; 4 passed with plutil, 2 passed and 2 skipped without.

### R55. make e2e tests whatever is already serving port 3100

- **Rank:** cosmetic (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `apps/web/playwright.config.ts:25`
- **Evidence:** The config sets `reuseExistingServer: true` on 127.0.0.1:3100. make dev and make demo-offline both serve the site on 3100, and the Makefile says make budget "Needs the built app running on 3100". scripts/harden_flaky.py itself says the config "reuses any server already on 3100 and would test somebody else's build". Scratch proof with Playwright 1.63.0: a stale server on a spare port served "OLD BUILD", and a webServer with reuseExistingServer true gave "served: OLD BUILD" and "1 passed". The webServer command never ran.
- **Outcome:** fixed. c98ed22: reuseExistingServer is process.env.PW_REUSE === "1", so false by default. Plain false would break make check: scripts/design-check.mjs starts this build on 3100 itself and runs design.spec.ts with PW_REUSE=1, and it relied on reuse. scripts/harden_flaky.py's docstring is updated. I read its code: it runs Playwright only when 3100 and 8100 are free, with CI set empty, so there is no retry and failOnFlakyTests is off, and it starts its own server as before. 7397af7 adds the PW_REUSE row to DEPLOY.md.
- **Proof:** Tests: an old server on the port gives 'is already used' and a nonzero exit, with and without CI. A free port starts the config's own server ('1 passed'). PW_REUSE=1 reuses it. Mutation reuseExistingServer: true made both 'refused' tests red. Mutation reuseExistingServer: false made the design-check reuse test red. Restored: 6 passed.

### R56. judge check says a dead proxy keeps it offline, but it sets no proxy

- **Rank:** cosmetic (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `scripts/judge_check.py:91`
- **Evidence:** offline_env's docstring says "no key, and a proxy that goes nowhere", and line 6 says "Every step runs offline". The function sets only SECOND_LOOK_OFFLINE=1 and NO_NETWORK=1. A search of the .py, .mjs and .ts files and the Makefile finds nothing that reads either variable, and no HTTP_PROXY is set (the Makefile's DEMO_ENV does set one). Only step 2 (make reproduce) has its own socket guard. I ran the Python suite with every outside socket refused in-process. It passed with "NONET tried: []", so nothing needs the network today, but nothing would stop it.
- **Outcome:** fixed. d39b06c: offline_env drops the two unused flags and sets HTTP_PROXY and HTTPS_PROXY to http://127.0.0.1:9 and NO_PROXY=localhost,127.0.0.1, in upper and lower case, because urllib lets the lower-case one win. New test test_the_tests_step_runs_with_no_key_and_a_proxy_that_goes_nowhere captures the env given to step_tests through main() and reads urllib.request.getproxies() in a fresh interpreter, with a real lower-case http_proxy set beforehand. The whole tests step passed under the new env: 'python: 1902 passed, 2 skipped, 11 xfailed', 'worker: pass 14'.
- **Proof:** Mutation 1: dropped the lower-case names; red ('http://proxy.example:8080' == 'http://127.0.0.1:9'). Mutation 2: set no proxy at all; red (KeyError 'https'). Restored: 8 passed.

### R57. verify_audit still passes an empty or shortened log, and judge check's audit step says ok

- **Rank:** cosmetic (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `scripts/verify_audit.py:35`
- **Evidence:** This is REVIEW_02 F73, still true in part. `verify_audit.py --path <empty file>` printed "audit-log: 0 entries, chain intact" and exited 0. The first two of three lines printed "audit-log: 2 entries, chain intact" and exited 0. judge_check.step_audit relies on this script. New since that review: with audit/log.jsonl emptied in a scratch copy, `pytest scripts/tests/test_ots.py` fails 3 tests, because the committed audit head proof names line 3. So make check and judge check's test step now catch it, while the audit step alone would still print ok.
- **Outcome:** fixed. 5c6fb44: verify_audit.py refuses a log with no entries unless --allow-missing. For the repository's own log, or with --proofs, it checks every proofs/audit-head-* copy through ots_status.stamped_line_gone, which now takes an optional log argument. The real log prints '3 entries, chain intact, 1 stamped line(s) still in place'. Tests: test_audit_log.py (empty log) and test_ots.py (cut back to 2 lines, and line 3 rewritten and relinked; plus the committed repo passes).
- **Proof:** The real audit/log.jsonl cut to two lines: 'audit-log: BROKEN: audit-head-2026-09-24: audit/log.jsonl has no line 3, the line this proof stamped', exit 1. The empty file exits 1. Mutation 1: 'if False and length == 0' made the empty-log test red. Mutation 2: 'gone = None' in stamped_lines made the lost-line test red. Restored: 40 passed.

### R58. The iNaturalist job test will fail from 2028 12 12

- **Rank:** cosmetic (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `scripts/tests/test_cache_inaturalist.py:215`
- **Evidence:** The mock sighting is dated "2025-12-11". main() takes its three-year cutoff from datetime.now (cache_inaturalist.py:325). I ran test_a_good_run_stores_one_row_per_creek_and_reads_it_back with cache.datetime patched to 2028-12-12. It printed "seen: none" and then raised AssertionError. With today's clock it printed PASS.
- **Outcome:** fixed. 3bfd61c: the run() helper in scripts/tests/test_cache_inaturalist.py pins cache.datetime to 2026-09-24 through clock_at(). New test test_a_good_run_does_not_hang_on_the_machines_clock sets the machine clock to 2028-12-12 before the run. The same plugin run now gives 17 passed.
- **Proof:** Mutation: removed the pin line from run(); the new test went red (1 failed, 16 passed); restored, 17 passed.

### R59. The D41 cause test says still blocked when python3 is missing

- **Rank:** cosmetic (lens: tests that prove nothing). **Checked:** reproduced by the fixer before the fix.
- **Where:** `docs/internal/DONE.md:126`
- **Evidence:** `env -i PATH=/nonexistent /bin/bash -o pipefail -c '! python3 -c "...getaddrinfo(...)" 2>/dev/null'` printed "cause test exit with python3 missing: 0". Bash could not find python3, and the leading ! turned exit 127 into 0. No lookup was made. done_check.judge reads exit 0 as "outside cause still holds", so D41 would stay BLOCKED and never go RED.
- **Outcome:** fixed. d99537d: in the D41 row of the DONE.md checklist the leading ! is gone. The cause test is now python3 -c $'...' with a try/except that exits 0 only on socket.gaierror and 1 after a lookup that works. New test test_the_d41_cause_holds_only_while_the_name_does_not_resolve runs the checklist's own cause test under bash -o pipefail. It uses a stand-in python3 (a symlink plus a sitecustomize stub, no network): name gone gives 0, name back gives 1, python3 missing gives nonzero. 'done_check.py --only D41' on this Mac still prints BLOCKED (the name really does not resolve).
- **Proof:** Mutation: restored the old D41 checklist row from HEAD; the test went red ('assert 0 != 0' for the python3-missing case); restored, it passed.
