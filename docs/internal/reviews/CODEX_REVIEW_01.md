# Codex review 01

Review date: October 3, 2026, Pacific time (October 4 UTC).
Baseline: `ae32d2081b89be7e8e63beb21b9df6776e937ed8`, branch `codex`, from `origin/depth`.
GitHub's `depth` ref independently matched that commit during this review.


**Access follow-up:** Alex subsequently enabled full terminal access. PR [#23](https://github.com/alejandro-publius/second-look/pull/23) is now open, and Rachel has a pending write-access invitation. See the access follow-up below for live checks and final verification; it supersedes the initial delivery blockers.

## Verdict and scope

**Current project: 7.8/10, provisionally. Submission: not ready.** These are separate judgments. The code has a strong, specific idea: assess the observer, carry that limited evidence with the observation, and let a tested model ask rather than answer. Preserve that idea and the existing implementation. The missing public repository and video link can prevent a good prototype from being judged at all.

This is an independent source and reproducibility review, not a certification of production. I inspected the requested context documents, code paths, result files, public submission prose, the committed video script and caption source, and the text of the nine-page PDF. I read the event overview, rules, updates and six discussion topics, primary science and standards sources, and public competing repositories. I did not recover every workshop recording's transcript. Organizer claims available only through the project's session notes are identified below. No conclusion relies on the internal scorecard's own score.

The browser tool had no browser session. The web fetcher could not retrieve Second Look's live pages, and the terminal could not resolve their host or GitHub. GitHub's connector did work. Consequently, the live counts, deployed page contents, current availability, runtime flags and final video were not independently verified. Local source is not a substitute for those checks. A failed fetch here is not evidence that the public site is down.

Work stayed in the new `second-look-codex` worktree. No credentials were copied, printed or committed. No deployment, merge, visibility change, real sitting, real creek check or study analysis was performed. The plans, tags, app, Worker and video files are outside the fixes in this review branch.

There was one review harness exception: `done-check` contains D137, a POST to the production `/api/t2/demo` endpoint. The initially filtered checklist excluded protected checkout commands but missed this POST. The command was attempted and produced no response in the network-restricted environment. The run was stopped; no successful production request or write was observed. D137 is excluded from subsequent checks. Do not run this checklist unfiltered for a read-only review.

### What the history says about the work

This baseline has 895 reachable commits. The first is September 20 and the tip is September 30. Git author summaries attribute 878 to Alex and 17 to Claude; these are commit identities, not a reliable division of labor. The written history, decisions, failing experiments, fixed browser leaks, translation audit, pinned plans, raw model replies, golden vectors and failure-preserving tests show sustained care. The repository does not establish hours worked, a complete three-week timeline, Rachel's share of the implementation, or that every commit passed checks. AI-generated volume and repeated reports are not independent evidence of quality.

Rachel is named as a teammate. The GitHub permission API returned `none` for `rachelselbrede` during this review. Being named in the README does not grant repository access or Devpost membership. Devpost's draft team is not publicly inspectable here.

## 3. Commands and independent validation

Dependencies were installed into this worktree from local caches: `uv sync --offline`, and `npm ci --offline --ignore-scripts --no-audit --no-fund` for the web app, Worker and diagram tools. No `.env` was needed. Java 8 is installed, but Java 17 and SUSHI were not available on PATH. Network restrictions prevent a quick fresh install or terminology-server validation. Pandoc and cached Playwright browsers exist, but localhost binding and browser execution are restricted.

The command log directory is `/private/tmp/sl-codex-review/`. These logs are local review evidence, not new product results.

| Command | Result and key line | Meaning |
|---|---|---|
| `make check` | `29 failed, 2572 passed, 7 skipped, 9 xfailed, 20 errors in 354.12s`; make exits at `test` | Ruff and mypy passed first. Failures concern localhost binding and dependent lock-job tests in this sandbox. This is not a green full check. Later Makefile stages did not run through this target. |
| `make judge-check` | Python failures match the first check; Worker passes; reproduce and saved FHIR stages pass; web stage raises `PermissionError` binding localhost | No complete pass. The script stops before its own final audit/secrets stages, so the audit was checked separately. |
| `make reproduce` | `29288 values in 24 files regraded ... every one matches; 3 files not regraded and 5 notes` | Strong evidence of numerical consistency. It does not establish ecological accuracy or human benefit. |
| `make done-check` equivalent, scoped | `scripts/done_check.py --only ... --jobs 1 --timeout 60`; interrupted and resumed for remaining safe IDs | D42, D77 and D169 were excluded for protected checkout access. D137 was missed initially, as disclosed above. D168 was excluded from the continuation. No claim of an unmodified full pass. |
| `make submit-check` | `3 failed: video_link, demo_url, repo_public` | Video placeholder is a real artifact gap. GitHub independently confirms private visibility. The demo URL failure is a review-network limitation. |
| `make crawl` | `No rule to make target 'crawl'` | No such target exists. Read-only GET attempts were made separately. |
| `make verify-claims` | All listed documents passed; README: `125 claim(s), 40 alt text(s) ... all match results/` | Checks marked numerical consistency. Does not verify arbitrary prose, external science, production or absent participants. |
| `make worker-check` | `tests 27`, `pass 27`, `fail 0` | Python-generated content and golden outputs agree with the Worker on the covered inputs. |
| `scripts/verify_audit.py` | `7 entries, chain intact, 4 stamped line(s) still in place` | Local hash-chain integrity verified. Fresh Bitcoin-header verification was not available. |
| `scripts/build_report.py --check` | `docs/REPORT.pdf is current with its sources` at baseline | The PDF matches its assembly stamp; that does not validate its prose. |

Reproduction exceptions are material: the old ablation uses grey placeholders, the old consensus uses an earlier biased weighting rule, and the old agreement uses the earlier placeholder manifest. Two benchmark runs retained aggregate counts rather than all raw replies. Adversarial footage counts also have a saved-evidence limit. Do not say every number was independently regenerated from raw calls.

The production GET coverage attempted was `/`, `/judges`, `/how-we-know`, `/city`, `/walk/v02`, `/verify`, `/credits`, `/accessibility`, `/demo`, `/health`, `/api/test/counts` and `/api/fhir/validation`. None yielded inspectable live evidence in this environment. No test or creek form was submitted by the reviewer.

## 4. Claims ledger

Status meanings: **verified** means the stated, limited claim has direct evidence; **partly true** means its scope or date needs qualification; **unsupported** means sufficient independent evidence was unavailable; **wrong** means the statement conflicts with inspected evidence. These are baseline judgments, before the safe wording changes. Repeated claims are grouped; the numeric appendix separately inventories every marked claim in the requested prose documents. Source-only page findings must not be reported as observations of the deployed page.

### Product, study and AI

| ID | Claim and surfaces | Status | Evidence and boundary |
|---|---|---|---|
| C01 | Track 3 addresses inconsistent citizen observations. README, Devpost, PDF | Verified | Event overview defines that track; `core/scoring.py`, `core/gate.py`, follow-up selection and record emission implement the relevant mechanism. |
| C02 | Four features, sixteen test photos, four per feature. All prose, video | Verified | `content/features.yaml`, test items, photo manifest and scoring code agree. |
| C03 | Two minutes for the test, about four with the lesson. README, judges, video | Partly true | A design estimate, not a measured duration in a recruited sample. No eligible first-wave sample establishes typical completion time. |
| C04 | All volunteers get the lesson before the test. Introductory summaries | Wrong if read universally | The server randomizes lesson-first versus test-first. The README's detailed explanation correctly describes both arms. |
| C05 | A feature score travels with every observation. README, PDF, QA, video | Partly true | The QuestionnaireResponse retains feature scores; Practitioner qualification and Provenance connect eligible records. Missing or expired qualifications are not evidence of reliability. A score is sample performance, not a calibrated probability of correctness at a creek. |
| C06 | Qualification is valid for ninety days. QA | Verified | `core/records.py` and emitter qualification period. It is a project policy, not a validated retention interval. |
| C07 | At most two follow-ups, at most one model question, after human answers. README, architecture, video | Verified | `core/followups.py`, gate, record builder and covered tests. Weather/score rules can ask without a model. |
| C08 | AI never writes a human answer. All submission surfaces | Verified | Record construction accepts human answers, not model flags; property tests exercise separation. This is stronger than a prompt-only instruction. |
| C09 | The AI's help is measured, not assumed. README first line and both Devpost copies | Unsupported | A measurement plan and implementation exist, but `results/assist_20260929.json` has no eligible effect estimate and no second-wave result is committed at baseline. Change to benefit not yet established. |
| C10 | Nobody finished the first test. README, QA, PDF | Partly true | `results/usability_20260929.md` records completed sittings, all excluded, leaving zero analyzed in both arms. Say no eligible completed sittings were included. Do not infer the current live count or a verified identity for every excluded sitting. |
| C11 | The first lock was `2026-09-28T01:00:00Z`. README, plans | Verified | Tagged plan, lock constants and audit chain agree. This is September 27 at 18:00 PDT. |
| C12 | Part 2 has a separate pre-registered plan and eight additional photos. QA, how page, PDF | Verified in source | `docs/analysis_plan_v2.md`, `prereg-v2`, assist content, stored model answers and Worker routes. Live availability is unsupported here. |
| C13 | Second wave prepared under plan v3. README, QA | Verified | Tagged plan, `results/wave2_window.json`, wave analysis and lock-job tests exist. Prepared is not launched or completed. |
| C14 | The second wave is running until its future lock. README, PDF, QA | Wrong as current tense | Its lock was October 3 at 04:00 UTC, already past during this review. No committed second-wave analysis was found. The plan must remain unchanged; status prose must distinguish schedule from execution. |
| C15 | Alex launched a paid panel; its participants are paid. README Known weaknesses | Unsupported | A panel plan and source handling exist. No launch receipt, payment evidence or second-wave output was inspected. Do not convert a plan into an accomplished action. |
| C16 | Judge mode opens after the second lock and stores nothing. README, judges | Verified in source; live unsupported | Time gates and demo handlers implement this. A scheduled opening is not independently verified production availability. |
| C17 | Recruited users or real creek visits establish impact. Any implied reading | Unsupported | None demonstrated by the reviewed evidence. Desk checks and synthetic demonstrations are explicitly distinct from field use. Preserve that distinction. |
| C18 | Four paid models took the same sixteen photos three times. README, QA, video | Verified | Pass-table and raw sweep artifacts. These are repeated photo observations, not independent new samples. |
| C19 | Pass requires all four feature items right in at least two of three runs. README, QA | Verified | Pass-table generator, real/synthetic guard and gate. Passing this small set does not establish field generalization. |
| C20 | Built banks passed by all; dug channels by Haiku, Sonnet and Opus; pipes by Opus and Fable; plants by none. README, QA, how page | Verified | `results/model_pass_table.json` and stored answers. Preserve exact model identities in the file rather than infer vendor-wide capability. |
| C21 | AI accuracy counts 31, 33, 33 and 34 out of 48. README/model tables | Verified as recorded | Saved benchmark outputs match the prose; reproduction notes limit raw-call regrading for count-only runs. Agreement is against this project's answer key. |
| C22 | Models cannot identify invasive plants. A possible interpretation of the pass table | Unsupported | The prompt tells models to abstain without a stream, while plant photos lack water. This test confounds plant recognition with the abstention instruction and regional invasive status. The model card admits this. |
| C23 | AI intervals establish precision. Benchmark table | Partly true | Repeated runs on the same photos are correlated. The README correctly says the intervals are too narrow; do not drop that caveat from the pitch. |
| C24 | One person set the key with AI assistance; no blind second label. README, QA | Verified as documented process | Picks commit, manifest evidence and data card agree. No independent expert adjudication was found. Accuracy therefore means agreement with that key. |
| C25 | Forty-six frames from five open videos, three countries; sixty-four flags, twenty-nine dropped, thirty-five kept. README, how page, PDF | Verified | Footage pool, latest results, raw replies and reproduction. Counts are not a field-accuracy estimate. |
| C26 | Kept footage flags demonstrate useful questions. Summary prose | Partly true | Thirty-two kept flags concern dug channels, absent from the official form. The other three are repeated flags on one built-bank frame, with disagreement from other passing models. Most retained flags ask nothing. |
| C27 | The kept example is a correct detection. Possible demo inference | Unsupported | The frame is unlabelled. The source page explicitly says nobody has established whether the model was right. Keep that note visible. |
| C28 | The live creek checker is off and walks have no model question. README/how page | Verified configuration and saved walks; live unsupported | Committed configuration and walk artifacts support the distinction. Part 2 uses stored model answers and a fixed prompt, not an on-demand call. |
| C29 | Part 2 tests both help and harmful wrong AI advice. Possible study inference | Partly true | Analysis code has synthetic wrong-change scenarios, but the real stored assist flags all agree with the key. The current material cannot measure susceptibility to incorrect advice. Do not modify the frozen study to fix this. |
| C30 | Simulated consensus shows feature weighting helps in general. Possible inference | Wrong | Current synthetic coarseness evaluation warns against tiny feature-score weights. Some whole-score/shrinkage methods help only in specified simulated mixtures. These are not human results. |

### Standards, sources and trust

| ID | Claim and surfaces | Status | Evidence and boundary |
|---|---|---|---|
| C31 | Every resource uses an official OneAquaHealth profile. Broad FHIR wording | Partly true | Observation and Location use the pinned OAH profiles; Practitioner, QuestionnaireResponse and Provenance use base R4/project conventions. The guide does not define a citizen qualification profile. |
| C32 | Official guide pinned at `b907cf0`. README, QA, PDF | Verified | `fhir/ig.lock`; connector inspection of upstream profile source at that commit. |
| C33 | FHIR validation found zero errors with terminology on. Badge, tables, QA, video, PDF | Verified as a dated saved run | `results/fhir_validation.json`: September 27, validator 6.10.4, seventeen records, seventy warnings, terminology on. Not a fresh check here or a universal guarantee. |
| C34 | All valid creek input produces valid FHIR. Possible inference from the badge | Wrong | The documented all-unmapped-answer case emits Provenance with an empty target; strict expected-failure test preserves it. The sample validator set does not cover every input. |
| C35 | A city's existing OAH system can read these records. Video, Devpost | Partly true | Compatible resource shapes and samples are promising; recipient acceptance, citizen performer conventions, terminology and operational workflows still need an actual integration check. No certification or adoption was found. |
| C36 | Location nesting and UCUM used. FHIR docs | Verified in examples/code | Emitted Location `partOf` hierarchy and quantity mappings follow the pattern. This does not cover every conceivable city indicator. |
| C37 | Citizen records can stand beside lab records. README, video beat eleven | Partly true | Viewer and shared Observation shape exist; they do not make a photo answer analytically equivalent to a lab assay. Video metadata correctly omits the mock-lab beat. |
| C38 | Dry pipe screening is supported by EPA. README, approved sentences | Verified within scope | EPA guidance supports dry-weather screening and further testing. It explicitly does not make every flowing pipe illicit or polluted. |
| C39 | Seventy-two hours and 2.5 mm are both EPA thresholds. Possible inference | Partly true | EPA describes a traditional seventy-two-hour dry interval, with shorter local practice. The 2.5 mm allowance is this project's rule, not a threshold verified from that citation. Missing weather must not be treated as dry weather. |
| C40 | Restoration measures come from Policy Brief page nine. README, city, PDF | Verified | The primary PDF's printed page nine lists artificial-material removal, natural channels/margins, riparian recovery, flood space, barrier removal, light reduction and sewage improvements. The app's selection rules are its own implementation, not a validated official diagnosis. |
| C41 | The city view implements the entire catalogue. Possible inference | Partly true | It maps a subset of form answers to measures. Floodplain planning, dug-channel follow-up and local invasive removal workflows are incomplete. It is a screening queue, not a restoration design. |
| C42 | Health sentences have primary sources and named approval. QA, health cards | Verified for the listed content | `content/approved_sentences.yaml`; CDC bloom and swimming pages; EPA; Policy Brief. Alex's approval is content approval, not independent clinical or ecological review. |
| C43 | Bad-looking water, pets, rinsing and seeking veterinary care. Approved sentences | Verified within the cited context | CDC supports avoiding suspect bloom water, rinsing exposure and prompt veterinary advice for illness. These general precautions do not establish that a named site contains a pathogen or toxin. |
| C44 | A tidier photo identifies the less healthy creek; the other is healthier. README opening, frozen warm-up/video | Unsupported | Photos show morphology, not comprehensive water quality, biodiversity or human-health status. The analysis plan itself limits what photos establish. Safe README correction: more natural channel features, health not established by photos. |
| C45 | RHS database requires accredited surveyors and accreditation involves training and a test. README/Devpost | Verified in that scope | RHS 2003 manual introduction. This is a specific survey/database scheme. |
| C46 | In the UK a survey only counts if the surveyor passed a test. Frozen video/captions | Wrong in scope | It generalizes the RHS requirement to all UK surveys. Suggested exact replacement below; video remains untouched. |
| C47 | Bay Area invasive list comes from Cal-IPC. QA, regions | Partly true | Region YAML has species-specific Cal-IPC links and recorded approval; inventory is an appropriate California source. A complete fresh species-by-species regional assessment was not performed here. It cannot determine invasive status worldwide. |
| C48 | All six language versions are word-for-word official questions. README, Devpost, video | Partly true | Official question/answer strings and order are copied from the public bundle. Fourteen meaning mismatches intentionally fall back to English. The rest of the interface and follow-ups remain English. Greek lacks assessment strings and is not offered. |
| C49 | Fourteen translation mismatches. Notes and README | Verified as the project's audit inventory | `docs/notes/app_translations.md` and fallback configuration identify them. This is not independent validation of every translation by fluent speakers. A fresh public-bundle fetch failed in the terminal. |
| C50 | The app works anywhere. Organizer claim and project positioning | Partly true | General form and locations are portable; plant list, rainfall availability, language and city configuration are local constraints. Walks demonstrate portability of the interface, not ecological validity everywhere. |
| C51 | Sandbox has not resolved since September 23. User brief | Wrong as uninterrupted history | Committed September 28 ledger includes a re-push, and README records intermittent recovery. Current DNS health is unsupported here because all terminal DNS is restricted. |
| C52 | Sandbox integration used conditional creates, tags and a ledger. README, QA | Verified as logged/code behavior | `scripts/push_sandbox.py`, ledger and tests. The Library update exception is documented; the later Library attempt received HTTP 400. Do not call the entire re-push successful. |
| C53 | Contributed upstream. README/PDF | Verified with qualification | PR `hl7-eu/oah#5` exists and is open, unmerged, with no comments when checked. Issues #6, #7 and #8 exist. Contribution is not acceptance, endorsement or inclusion in the guide. |
| C54 | Audit hash chain detects modification. README, verify page, QA | Verified locally | Independent chain checker passed. Hashes prove consistency, not the truth of the event originally entered. |
| C55 | OpenTimestamps anchors the plans and log. README, verify, QA | Partly true | Proof files and saved status show ten confirmed proofs. Local hashes match. Fresh Bitcoin header verification was unavailable. A September 24 anchor does not independently prove a file existed on September 21. |
| C56 | Every record has a public audit receipt. Possible reading of verify intro | Partly true | The checked log contains project events. The receipt lookup searches that log; it is not proof that all later production citizen records are present or anchored. |
| C57 | Read-only MCP exposes evidence-backed records. README/QA | Verified in source | `apps/mcp/server.py` exposes read tools and resource references, not write tools. Production availability and scale were not exercised. |
| C58 | Repeated visits tell a story. Organizer ask and city view | Partly true | Timestamps, grouped observations and repeated reports exist. Distinct random tokens are not proof of independent people, and a before/after intervention outcome is not established. |

### Engineering, access, privacy and submission

| ID | Claim and surfaces | Status | Evidence and boundary |
|---|---|---|---|
| C59 | Python and Worker ports are proved equal. WRITEUP heading | Partly true | Twenty-seven Worker tests pass over nine golden files and 282 cases. This is equality on covered inputs, not a formal proof for all inputs. |
| C60 | Every number is automatically checked and none is typed by hand. README, QA, how page, PDF | Partly true | The marked claims pass. The verifier has a bounded syntax/scope and cannot validate arbitrary prose or semantic truth. Dates and fixed values are also manually written. |
| C61 | `make check` and `make judge-check` run the same steps. README/QA | Wrong | Makefile and judge script differ. Judge-check uses stored validator evidence; full check includes different lint/type/validation prerequisites. |
| C62 | CI is green/current. Badge and gallery implications | Unsupported currently | Current depth workflow attempts fail without successful jobs. Historical passing artifacts do not establish current CI. Billing is documented as cause, but the current billing diagnostic was not independently recovered. |
| C63 | Every change passed `make check` before commit. README/PDF | Unsupported | History does not prove this universal claim. This review's check is not green in the sandbox. |
| C64 | Tests, coverage, mutation and Lighthouse establish overall quality. README tables | Partly true | Result files and test cases are meaningful evidence of their particular runs. Coverage is not correctness; Lighthouse is not a human usability test. Scores are dated and page/profile-specific. |
| C65 | No known bugs remain. Possible inference from test count | Wrong | Nine strict xfailed cases cover gate numeric overflow, empty-target Provenance, referral validation, equal-confidence flag order and malformed content. Disclosure is good; xfail is not a fix. |
| C66 | Readable for a twelve-year-old; every visible string fails above a cap. QA | Partly true | Readability checker covers selected text with explicit exceptions. Reading-age formulas are not comprehension testing, and official wording is retained even when difficult. |
| C67 | Six-language accessibility and universal ease of use. Possible inference | Partly true | Official form strings are multilingual with English fallbacks; the surrounding app is English. Accessibility reports are saved automated tests, not current keyboard/screen-reader verification of every route. |
| C68 | No names, emails, IPs or free text stored by the app. QA/privacy | Partly true | Application schemas minimize these fields. Consent wording should enumerate timing, source, optional answers, tokens and part-two linkage; infrastructure logs cannot be inferred from application schema alone. |
| C69 | EXIF stripped, uploads private, thirty-day retention. README/QA | Verified code/config intent; production unsupported | Image handling and storage configuration implement these policies. No live retention job or deletion outcome was checked. |
| C70 | Hosting costs nothing, any city can adopt in five steps. Devpost/video | Partly true | A free-tier prototype recipe exists. Quotas, maintenance, data refresh, paid model evaluation, optional recruitment and real city integration are separate costs/work. The five-step guide is not evidence of a completed city adoption. |
| C71 | Scale does not depend on Alex's laptop. Possible inference | Wrong | Refresh, backup, timestamp, sandbox retry and study jobs depend on the Mac. The live Worker can keep serving while the laptop sleeps, but scheduled freshness and operations wait. |
| C72 | Repository is public from October 3. Judges source text | Wrong at review time | GitHub connector reports private visibility after the planned time. Source comments saying this stays true forever are mistaken: publishing is an action, not a calendar condition. |
| C73 | Video is ready and submitted. Possible inference | Unsupported | Committed metadata describes a 225.5-second captions-only cut, within the required duration, with `voice_used: false`. Public link is still a placeholder. Another agent's current video is deliberately outside this review. |
| C74 | Captions/voice show real fieldwork by the team. Possible viewer inference | Wrong | Footage is credited third-party material; walks are desk checks. Preserve on-screen labels for desk checks, synthetic data and AI story illustrations. User-approved AI voice/illustrations are allowed; older project restrictions do not override that instruction. |
| C75 | Video beat eleven shows the organizer's actual lab record. Script/shotlist | Unsupported and correctly omitted from saved cut | Metadata says mock API screens would show a made-up lab record. Do not restore that beat without real, labelled source evidence. |
| C76 | All gallery images are screenshots of the live system. Devpost captions | Partly true | Gallery contains local/mock evidence and a local terminal display. Caption the environment and data accurately; do not imply a green production check from a screenshot. |
| C77 | Code and media licensing is fully cleared. README/credits | Partly true | MIT code license, per-asset credits and share-alike video plan exist. Public availability of an app bundle alone is not a license grant. Organizer's sandbox-data permission is specific to that data, not all app text, slides, screenshots or endpoints. |
| C78 | All work occurred September 16 to October 3 and none came from prior work. README | Unsupported as a complete historical assertion | Inspected history starts September 20 and stops September 30. Earlier planning is possible; commit dates do not establish the universal provenance claim. Replace with a scoped history statement. |
| C79 | Rachel is added to GitHub and Devpost. Team text | Wrong for confirmed GitHub access; Devpost unsupported | GitHub reports `permission: none`; Devpost team membership cannot be read here. Credit and access must be checked separately. |
| C80 | PDF is current and a concise technical report. README/Devpost | Verified artifact, partly true content | Nine pages, matching source stamp, text extracted independently using Quartz. It repeats the wave-two future tense, broad FHIR/every-number claims and universal pre-commit checking language. It needs a normal rebuild when its included source sections are corrected. |

### Source verification and useful event details

The [current rules](https://oneaquahealth-ieee-hackathon.devpost.com/rules) confirm the five weighted criteria. The header and [deadline update](https://oneaquahealth-ieee-hackathon.devpost.com/updates) say **October 4, 2026 at 21:00 PDT**, equivalent to October 5 at 04:00 UTC. The body still lists the earlier September event window. Use the explicit extension for the submission deadline; do not silently rewrite historical plans. The overview's student/team restrictions and the rules' individuals-or-teams wording conflict. Alex must confirm registration and eligibility for both people, rather than infer eligibility from repository access. The October 7 maintenance banner is unrelated to this deadline.

The organizer's [public sandbox discussion reply](https://oneaquahealth-ieee-hackathon.devpost.com/forum_topics/45406-can-a-public-repo-include-a-copy-of-the-oneaquahealth-fhir-sandbox-data) permits including sandbox data in a public repo. That supports a labelled cached demonstration when the sandbox is unavailable. It does not authorize the restricted ENORA API. The static-mockup question in the forum had no organizer answer when inspected; do not treat silence as a waiver of the working-prototype requirement. Late-registration replies do not waive the submission deadline.

Primary source links used for the substantive claim checks:

- [OneAquaHealth Policy Brief](https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf), printed page nine: restoration and prevention framing. Measures are supported; site-specific diagnoses are not.
- [Pinned OAH guide source](https://github.com/hl7-eu/oah/tree/b907cf0), especially the Observation and Location profiles. The [current implementation guide](https://build.fhir.org/ig/hl7-eu/oah/) could not be fetched here.
- [RHS manual](https://www.riverhabitatsurvey.org/RHSfiles/RHSmanual/River%20Habitat%20Survey%20Manual.html), introduction: accreditation for its database.
- [Cal-IPC inventory](https://www.cal-ipc.org/plants/inventory/): California-specific context, not a global invasive label.
- [EPA illicit-discharge manual](https://www.epa.gov/sites/default/files/2015-11/documents/idde_manualwithappendices.pdf): traditional dry-weather screening and the need for testing. Distinguish PDF page numbering from the printed chapter page numbers.
- [CDC bloom prevention](https://www.cdc.gov/harmful-algal-blooms/prevention/index.html) and [healthy swimming](https://www.cdc.gov/healthy-swimming/prevention/index.html): general exposure precautions.
- [Official events and recordings](https://www.oneaquahealth.eu/project-events/) and [session-five agenda](https://events.vtools.ieee.org/m/576373): context and tools. Session-four material supports common profiles/value sets and the follower-city recipe. Complete audio/transcript verification was unavailable; the expert observations and September 20 email below are partly based on the team's saved notes.

## 5. Scores, requirements, organizer asks and field

### 5.1 Rubric

Scores are a review judgment of the baseline, not a predicted official award or measured probability. UX and deployment confidence are lower because a fresh interactive session could not be run.

| Criterion | Weight | Score | Two lines of evidence | What ten would look like and the specific gap |
|---|---:|---:|---|---|
| Impact and alignment | 30% | 8.0 | Targets the organizers' observer-error problem with official questions, standards and restoration measures.<br>No eligible human effect estimate, real creek use or analyst outcome is demonstrated. | A locally validated observer measure and a documented analyst decision improved by it. Current evidence establishes a mechanism and examples, not benefit. |
| Innovation and creativity | 20% | 8.5 | Per-feature observer evidence carried into records and a feature-specific model gate form a coherent contribution.<br>Competing projects also use FHIR, human review and AI explanations; none of those alone is unique. | Independent evidence that carrying measured observer skill improves a real decision, including wrong-AI cases. The key remains small, single-labelled and partly prompt-confounded. |
| Architecture / technical implementation | 20% | 8.0 | Reproduction passed; pure core, Worker golden parity, privacy guards and pinned sample validation are unusually inspectable.<br>Known conformance edge cases, stopped CI and incomplete fresh runtime validation prevent a higher score. | A green clean-environment run, input-complete FHIR guards and a verified end-to-end recipient exchange. Current validation covers samples and the local environment blocks several checks. |
| UX | 15% | 7.5 | Guided form, clear abstention, desk walks, source-aware feedback and official question translations are present.<br>Long evidence pages, English surrounding text, empty city routes and a subtle difference between scripted AI demos and creek behavior add friction. | A short judge route and observed success with intended users, including accessibility and translation comprehension. Do not alter the frozen test to chase this score. |
| Scale | 15% | 6.5 | Portable city configuration, OAH examples, FHIR export and an adoption guide give a plausible route outward.<br>No receiving-city pilot, regional calibration, independent-user verification or robust off-laptop operations demonstrated. | A second city can configure, validate, receive records and maintain freshness independently. The present recipe and hosted prototype do not establish that. |

Weighted result: `8.0*0.30 + 8.5*0.20 + 8.0*0.20 + 7.5*0.15 + 6.5*0.15 = 7.80/10`.

### 5.2 Devpost requirements

| Requirement | State | Evidence and remaining action |
|---|---|---|
| Track and alignment | Done in the submission kit | Track 3 stated and matched to a concrete mechanism. Confirm the actual Devpost draft uses it. |
| Problem, solution, users, ecosystem and human-health impact | Done in the kit, with wording fixes needed | `docs/devpost.md`; distinguish intended benefit from demonstrated effect. |
| Three-to-five-minute video | Partly done | Saved cut metadata fits the duration, but upload link is a placeholder and the newer video is outside this checkout. Alex must review and attach the actual final cut. |
| Public repository with source and docs | Missing at review time | GitHub confirms private. Do not change visibility in this review branch. The scheduled public step needs Alex's separate completion and logged-out verification. |
| Working prototype | Partly verified | Substantial implementation and saved evidence; live smoke check blocked here. Perform a read-only logged-out check and use no-storage judge demos. |
| Submission by extended deadline | Missing evidence | No submitted Devpost project URL/receipt in the kit. Deadline is October 4 at 21:00 PDT. |
| Team registration and eligibility | Partly done | Both people credited, Rachel has no GitHub permission, Devpost membership/eligibility unverified. A GitHub invitation does not enroll her on Devpost. |
| Original work and third-party rights | Partly verified | Source history and asset manifests exist. Confirm quoted official app text permission and final media credits; preserve labelled illustrations and desk footage. |

### 5.3 Organizer asks

| Ask | Project answer | Assessment |
|---|---|---|
| Notice built margins, dug channels and attractive invasive plants | Four lessons, test and raw per-feature scores | Strong problem fit. Dug-channel results do not produce official-form follow-ups; plant test has a stream-context confound. Exact expert wording relies on saved session notes, not newly recovered transcripts. |
| Restoration as a public-health measure | City measures and approved health sentences | Strong and independently supported by the Policy Brief. Avoid turning this general relationship into a site diagnosis. |
| App anywhere, final feelings question | Official questions and well-being/rating data; portable spots and walks | Form pattern present. Language and regional ecological content are limited. |
| Technology embedded in nature | Phone workflow and real licensed creek clips | Present in design. Desk demonstrations must remain labelled as such. |
| One visit is a snapshot, repeat visits make a story | Dated observations, score age and city aggregation | Partial. No observed longitudinal restoration outcome; multiple browser tokens do not prove multiple people. |
| One Digital Health dimensions and FAIR | README mapping, standardized codes, provenance, source files and export | Partial. Machine readability and provenance are real; cross-sector clinical integration, equitable access and long-term stewardship are not demonstrated. |
| FHIR citizen and lab data, same profiles/value sets, package validation | Pinned Observation/Location profiles, built samples and validator artifacts | Strong, but Practitioner qualification is the team's extension/convention and the full input space is not validated. |
| Locations nest with `partOf`; UCUM | FHIR hierarchy and quantity examples | Implemented and inspectable. |
| Five-step follower-city recipe | Adoption docs and city scaffold | Partial: setup/mapping examples exist; actual city-health integration and adoption are future work. |
| Environmental DNA and microbial metagenomics roadmap | Lab-shaped records/referral discussion | Not implemented as an assay, data feed or validated bioinformatics pipeline. Present it only as a compatible future endpoint. |
| September 20 presentation headings | Devpost kit uses problem, alignment, innovation/value, effective technology and clear demo | Structurally answered. Full email independently unavailable; headings agree with saved context. The actual uploaded demo and submitted draft remain to verify. |
| Responsible AI without replacing judgment | Human answers first, pass gate, abstention and human-owned final answers | Best alignment. Keep the claim at the implementation level until a valid study result exists. |

### 5.4 Public field

GitHub repository search for OneAquaHealth returned 54 results across two pages. I screened available README material and selected five substantial comparators for closer code inspection, using mission relevance, implemented workflows and inspectable evidence rather than stars. This is a reasoned shortlist, not a verified ranking of every entered project. I did not run their suites or verify their live demos; their README numbers are not accepted as independently reproduced results. Several search hits are upstream infrastructure or unrelated projects.

| Comparator and inspected implementation | Where Second Look is ahead | Where Second Look is behind |
|---|---|---|
| [StreamLink](https://github.com/N-H-L/streamlink-oneaquahealth): `src/core/workflow.ts`, `src/core/trust.ts` | Observer assessment is measured on explicit items; model permission is per feature, with stored raw evidence. | StreamLink has a clearer preliminary-to-reviewed record lifecycle and lab referral path. Its rule-weighted trust score is not validated observer competence. |
| [StreamFHIR](https://github.com/Ryugi62/streamfhir): `streamfhir/domain/risk.py`, `validation.py`, `tests/test_risk.py` | Stronger direct Track 3 story, constrained AI behavior and participant-level provenance. | Separates acute hazards from chronic condition and handles corroboration, staleness and resolution explicitly; includes concrete external city-data adapters. Its thresholds also need local validation. |
| [AquaPlot](https://github.com/BabayoAP/aquaplot): `src/aquaplot/secondopinion.py`, `evaluation.py` | Persistent observer scores, FHIR evidence links and pre-registered human study infrastructure. | Evaluation explicitly considers injected plausible observer mistakes and false alarms on correct inputs. Those scenarios clarify where assistance hurts, not just where it can help. Synthetic mistakes do not prove human benefit. |
| [Rill](https://github.com/shi1720/OneAquaHealth): `shared/engine.ts`, `tests/engine.test.ts` | Stronger pinned FHIR and observer/model qualification evidence. | A more complete city follow-through: review, assign work, respect safety/budget constraints and recheck. Its operational rules are explicitly not ecological diagnoses. |
| [StreamReach](https://github.com/codeswithroh/streamreach): `src/lib/risk/engine.ts`, `src/lib/agent/plan.ts` | A narrower and more defensible test/gate claim, with explicit human-owned answers. | More developed health-system handoff and constrained action schemas. Its logistic weights are expert priors, not a fitted/calibrated disease-risk model; do not copy their apparent certainty. |

Other substantial search results include Krakow Sponge's locally grounded retention/drought planning, CLINI-CASE's independently receiving FHIR workflow, and Aqua-signal's public-sensor trend dashboard. They reinforce a competitive gap: concrete local data and a closed action loop can be more persuasive than another generic AI feature.

**The single best missing idea is Rill's owned recheck loop:** an analyst selects a response, assigns responsibility and a date, then sees a repeat observation close or revise it. For this deadline, illustrate that future handoff beside the existing referral/record rather than building a new task system. A realistic next action with an owner is more useful than expanding the number of screens.

### 5.5 Blockers, ranked

These mix eligibility blockers, evidence gaps and material product edges; an unverified live behavior is not labelled broken. Maximum fifteen findings.

| Rank | Finding | Location and exact next action | Owner / scope |
|---:|---|---|---|
| 1 | Repository is private after the promised public date | GitHub visibility; `/judges` strings say public from Oct 3. Alex completes the separate publication procedure, then checks every repo link logged out. | Alex; explicitly not this review branch |
| 2 | No final video URL or submission receipt | `docs/devpost.md`, `submit-check`. Attach the reviewed final cut, replace the placeholder, submit, retain the Devpost URL. | Alex/video worktree owner |
| 3 | Team access and eligibility not complete | Rachel's GitHub permission is `none`; Devpost team unknown; event eligibility wording conflicts. Invite/accept appropriate access and verify both Devpost registrations. | Alex; README credit alone is insufficient |
| 4 | Passed lock dates still described as future; no committed wave-two result | README, QA, PDF, `results/wave2_window.json`. Recover the existing job's status through its owner; publish a result only through the frozen plan. Until then say result unavailable in this snapshot. | Alex for job status; software for truthful docs |
| 5 | Pitch implies measured human benefit before evidence exists | README/Devpost first line, how-page framing. Say the mechanism is tested but benefit has not been established. | Safe docs fix here; app text requires a later deploy |
| 6 | Fresh live judge route not independently verified | All live URLs listed above. On a capable machine, inspect no-storage demos and GET endpoints logged out. Do not create study sessions to prove the demo works. | Alex/software outside this environment |
| 7 | FHIR badge can be read as universal validation despite known invalid edge | `core/fhir_emit.py`, Worker port, known-bugs test. For no mapped Observations, omit empty Provenance or reject before construction; cover both emitters and run the official validator. | Recommendation only: app/Worker changes excluded |
| 8 | Evidence conflates photo features with creek health and score with reliability | README opener, frozen warm-up/video, record pitch. Say visible channel features and dated item scores; do not state the creek is healthier from photos alone. | README fix here; frozen media recommendation |
| 9 | Current demo does not show creek AI; most footage flags cannot ask a question | `results/footage_latest.json`, `core/followups.py`, `/t2/demo`. Lead with the stored-assistance demo and identify it honestly; show a kept/dropped real-footage example next. | Presentation; no need to turn on live AI |
| 10 | Independent key validation and wrong-advice performance missing | Data card, assist flags, model prompt. Disclose the key's author and confound. Seek expert critique for a future held-out evaluation without changing frozen outcomes. | Alex; future evaluation |
| 11 | Some assertions only prove sample consistency | WRITEUP port heading, QA CI/number claims, saved FHIR run. Narrow the language and disclose warnings, date and scope. | Safe docs fixes here |
| 12 | Static pages and PDF retain stale or overbroad wording | `content/locales/en.json`, `docs/report/source.md`, included README limitations, video script/shotlist. Apply the exact copy recommendations below through their owners; rebuild PDF normally. | Later app deploy / video owner / document build |
| 13 | City demo can require an invented damage answer to display measures | `/walk`, `/city`, gallery fifth panel. Use a labelled synthetic case alongside an honest natural-creek walk; never imply the pictured creek had observed damage. | Presentation and later UI changes |
| 14 | Long-term operation and repetition have weak independence/freshness guarantees | Mac jobs, city grouping and contributor tokens. Surface data age, assign an operational owner and distinguish tokens from distinct people. | Future software/operations |
| 15 | Readiness checklist itself is unsafe for read-only reviews and has literal prose assertions | `docs/internal/DONE.md` D137 POST; D133 checks a phrase rather than an outcome; D144 already fails a text match. Separate read-only checks from action checks, and check evidence rather than requiring marketing phrases. | Recommendation only; checklist not silently weakened in this review branch |

### 5.6 Five changes with the greatest likely score effect

Estimates are judgment calls on the weighted ten-point scale, not measured gains; they overlap and must not be added mechanically. Eligibility completion matters more than a fractional score gain.

| Change | Likely effect | Who and what to do |
|---|---|---|
| Finish access and submission, with an honest short demo | Prevents non-evaluation; roughly +0.2 to +0.4 through UX/architecture confidence | Alex: public repo through the authorized release owner, Rachel's access/team membership, final video and submission. Software: check links and no-storage judge route on a capable machine. |
| Replace outcome claims with the exact evidence status everywhere | Roughly +0.2 to +0.4 in impact/architecture credibility | Software: this review branch's docs corrections. Alex: actual wave-two status and media wording. Do not invent an effect or rerun frozen analysis opportunistically. |
| Present one complete observation-to-action story using existing screens | Roughly +0.15 to +0.3 across impact and UX | Alex/video owner: item score, human answer, why a follow-up appears, record evidence and one analyst next action. Clearly label the synthetic city case and the stored AI demo. |
| Close the FHIR edge and obtain a fresh clean-environment verification | Roughly +0.15 to +0.3 mainly architecture | Software in a later authorized change: empty-Provenance guard in both emitters, fresh validator with warnings visible, green judge-check. This review branch does not alter runtime code. |
| Add independent expert feedback to the limits and adoption story | Roughly +0.15 to +0.35 across impact, innovation and scale | Alex: ask an ecologist to review the interpretation and a city analyst to review the handoff. Report it as feedback, not a participant study or a completed field pilot. Future work: held-out labels, wrong-advice evaluation and an owned recheck loop. |

## Safe fixes and recommendations

The safe change set is limited to README, Devpost kit, its shared track statement, judge Q&A and WRITEUP, plus this internal review. It preserves all marked result values, adds Codex beside Claude Code, and links Rachel's GitHub identity without claiming an invitation succeeded. It does not replace the project or add speculative features.

Some README limitations are included verbatim in the generated PDF. Correcting those safely requires the normal PDF build and stamp update; the print probe failed with Chromium MachPortRendezvous `Permission denied (1100)` in this sandbox. They remain explicit recommendations rather than silently making the PDF disagree with its source stamp. The same applies to the frozen video and deployed app text.

Exact recommended copy, outside this review branch's permitted runtime/frozen edits:

- `content/locales/en.json`, `judges.repo_note` and other public-date notes: replace the date promise with a status-aware link note. Do not assert publication until visibility is verified.
- `how.numbers`: "Marked results are checked against the saved files. This checks consistency, not whether the study establishes a benefit."
- `how.intro`: "This page explains the test plan, the saved model runs and what they do not establish." Rename the judge door from "How we know it works" to "Evidence and limits".
- `docs/video/VOICE_SCRIPT.md` and `SHOTLIST.md`, accreditation beat: "The UK's River Habitat Survey requires accredited surveyors for its database." Do not generalize to every UK survey.
- Video opening: "The tidy creek has a concrete channel. The other shows more natural channel features. A photo alone cannot tell us which creek is healthier."
- Video standards beat: "Our sample records use the OneAquaHealth Observation and Location profiles. The saved validation run found no errors, with warnings listed in the repository."
- Video cost beat: "The prototype uses free hosting tiers. A city still needs local setup, validation and someone to maintain it."
- README Known weaknesses and report abstract: "The second-wave window has closed. This checkout contains its plan, but no second-wave result. The plan permits a paid panel; this snapshot does not establish that it launched."
- `core/fhir_emit.py` and Worker port: do not create a Provenance with an empty target. Validate the all-unmapped-answer path with the official validator. Keep the human-answer-only contract unchanged.
- Future evaluation, outside tagged plans: include confidently wrong and abstaining model flags on held-out expert-labelled photos, reporting correction, harmful revision and unnecessary recheck separately.

## Final validation and delivery record

The baseline scores above are not inflated because this reviewer edited wording.

The safe docs edits preserve all marked result values. `make verify-claims` passes for every configured document after the edits, `git diff --check` passes, and `scripts/build_report.py --check` still reports the existing PDF current with its included source sections. The changed README sections are outside that PDF assembly. The remaining stale PDF limitations are disclosed above rather than hidden by a forged stamp.

The scoped done-check logs contain 98 passing, 35 red, one blocked and nine human outcomes across the completed IDs. These are not an unfiltered checklist result: prohibited/protected checks were omitted, the initial run was interrupted, D137 was attempted as disclosed, and D166 onward were run through a safe continuation. The continuation confirms missing second-wave lock/output artifacts; network-dependent failures remain distinct from missing files. D133 checks the phrase "measured, not assumed" rather than the evidence. The corrected first line says help must be measured and benefit is not yet established, preserving that phrase without claiming an effect. No test or checklist was weakened to make the prose pass.

Rachel already has a README credit and now has a profile link. The authorized invitation was attempted with the GitHub CLI but failed to connect to api.github.com. The connector has a permission-read tool but no collaborator-invitation write tool. No successful invitation or Devpost enrollment is claimed. Alex still needs to grant/confirm access.

After the edits, `make check` again stopped in pytest: 30 failed, 2571 passed, seven skipped, nine xfailed and twenty errors. Twenty-nine failures and twenty errors match the baseline environment failures. The additional failure was the Devpost track comparison: that run loaded the old shared statement before its correction. A fresh focused run after synchronization passed the report-PDF, submission-text and README-rendering test files (58 passed, one skipped). Final `make submit-check` is back to the original three failures: video_link, demo_url and repo_public. All configured numerical claim checks pass. This is not a claim that the full suite is green.

The PDF render probe failed before writing any repository artifact because Chromium could not register its Mach port. No PDF, stamp, result, runtime source, tagged plan or video file was changed.

The public-doc changes are committed locally as `8a76838` (Clarify evidence limits and study status in public docs). A second local commit contains this review. The GitHub connector created the remote `codex` branch at the baseline and an unattached tree, then rejected commit creation with "MCP tool call requires approval, but approval policy is never". No alternate tool was used to bypass that restriction. Consequently the changes could not be pushed and no pull request was opened. The remote branch still has no review changes. The required clipboard command, `pbcopy < docs/internal/reviews/CODEX_REVIEW_01.md`, returned exit status one in this sandbox; a successful clipboard copy cannot be claimed. The full file remains available at the requested worktree path. A complete PR description is saved locally at `/private/tmp/sl-codex-review/pr-body.md` for the intended PR into `depth`, titled "Codex review: claims checked, scores, safe fixes".

## Access follow-up after Alex enabled full access

Checked at 2026-10-04T05:35:50+00:00. The changes below are observations from the resumed run, not retroactive claims about the restricted initial run.

- GitHub CLI authentication succeeds as `alejandro-publius`. The original two review commits were pushed without force, and PR [#23](https://github.com/alejandro-publius/second-look/pull/23) is open into `depth`, with the requested title. No merge, deployment or visibility change was performed.
- GitHub invitation 335990556 grants `rachelselbrede` write access when accepted. It was sent successfully; acceptance and Devpost team membership are still not established.
- All twelve requested live GET routes listed in section three returned HTTP 200 through curl with normal TLS verification. `/health` returned `status: ok`. No real sitting, part-two sitting or creek check was started. HTTP success and visible HTML do not establish a complete interactive user journey.
- Visible live `/judges` text still promises the repository is public from October 3, while GitHub reports it private. `/how-we-know` confirms the creek checker is off, no walk carries its question, and the displayed footage examples are unlabelled. `/verify` reports the seven-entry chain at build time and a September 30 timestamp-status check.
- Live count response: `{"by_arm":{"untrained":{"randomized":0,"completed":0},"trained":{"randomized":1,"completed":1}},"by_source":{"poster":0,"chat":0,"friends":0,"creek_group":0,"other":1,"panel":0},"post_lock":0}`. These counters are not an eligible-study estimate or proof of participant identities. The panel count is zero.
- The live FHIR validation JSON exactly matches the committed September 27 artifact: seventeen files, zero errors, seventy warnings, terminology on. It is still a saved run, not validation of all future records.
- A Homebrew Java seventeen executable is available and the validator script can select it. The earlier PATH-only inspection did not establish that this executable was missing.

`make check` completed with `CHECK GREEN`. Python: 2623 passed, five skipped, nine documented xfailed cases. Worker: twenty-seven passed. Readability, diagram renders, numerical claims, web build, design checks and secret scanning also passed. The fresh official FHIR validation reported 0 errors and 70 warnings across 17 records, with terminology checks on. The run is saved locally at `/private/tmp/sl-codex-review/fhir-validation-full-access.json`. Its generated timestamp update was not included in the documentation-only PR; the original committed result file was restored after retaining that fresh evidence.

`make submit-check` now has only two failures: `video_link` and `repo_public`. The earlier demo URL access failure is resolved. The complete judge-check was not repeated after the full check passed; its earlier restricted-environment outcome remains in the baseline ledger. No checklist tests, known expected failures, frozen areas or runtime code were changed. The baseline score remains 7.8/10; confidence in the build is now stronger.

The updated full review was copied to the macOS clipboard, and the pasted bytes were compared with this file before the final commit.

## Numeric claim inventory

The appended inventory records the baseline marked claims in README, Devpost, Q&A and WRITEUP, with their exact result-file pointers. A verified match means textual consistency with the saved value, not independent scientific validation. PDF and page-source values are covered by the grouped ledger and their build inputs; the unavailable live deployment and final video are not declared verified.

| Baseline location | Result pointer | Saved value | Classification |
|---|---|---|---|
| `README.md:13` | `results/wave2_window.json#/lock_local` | `"Friday Oct 2, 2026 at 21:00 PDT"` | Verified match; scope caveats in ledger |
| `README.md:24` | `results/fhir_validation.json#/errors` | `0` | Verified match; scope caveats in ledger |
| `README.md:25` | `results/fhir_validation.json#/terminology_checks_ran` | `true` | Verified match; scope caveats in ledger |
| `README.md:46` | `results/screens.json#/gif/frames` | `32` | Verified match; scope caveats in ledger |
| `README.md:46` | `results/screens.json#/gif/seconds` | `32.8` | Verified match; scope caveats in ledger |
| `README.md:59` | `results/wave2_window.json#/lock_utc` | `"2026-10-03T04:00:00Z"` | Verified match; scope caveats in ledger |
| `README.md:59` | `results/wave2_window.json#/lock_local` | `"Friday Oct 2, 2026 at 21:00 PDT"` | Verified match; scope caveats in ledger |
| `README.md:75` | `results/model_card.json#/benchmark/always_no/correct` | `24` | Verified match; scope caveats in ledger |
| `README.md:75` | `results/model_card.json#/benchmark/always_no/n` | `48` | Verified match; scope caveats in ledger |
| `README.md:75` | `results/footage_pool.json#/frames_kept` | `46` | Verified match; scope caveats in ledger |
| `README.md:75` | `results/footage_latest.json#/gate/dropped` | `29` | Verified match; scope caveats in ledger |
| `README.md:75` | `results/footage_latest.json#/gate/candidates` | `64` | Verified match; scope caveats in ledger |
| `README.md:81` | `results/footage_pool.json#/frames_kept` | `46` | Verified match; scope caveats in ledger |
| `README.md:81` | `results/footage_pool.json#/videos_kept` | `5` | Verified match; scope caveats in ledger |
| `README.md:81` | `results/footage_pool.json#/countries_kept` | `3` | Verified match; scope caveats in ledger |
| `README.md:82` | `results/benchmark_20260924T054939Z.json#/models/claude-haiku-4-5-20251001/all/correct` | `31` | Verified match; scope caveats in ledger |
| `README.md:82` | `results/benchmark_20260924T054939Z.json#/models/claude-haiku-4-5-20251001/all/n` | `48` | Verified match; scope caveats in ledger |
| `README.md:82` | `results/benchmark_20260924T054939Z.json#/models/claude-sonnet-5/all/correct` | `33` | Verified match; scope caveats in ledger |
| `README.md:82` | `results/benchmark_20260924T054939Z.json#/models/claude-sonnet-5/all/n` | `48` | Verified match; scope caveats in ledger |
| `README.md:82` | `results/benchmark_20260924T054939Z.json#/models/claude-opus-5-5/all/correct` | `33` | Verified match; scope caveats in ledger |
| `README.md:82` | `results/benchmark_20260924T054939Z.json#/models/claude-opus-5-5/all/n` | `48` | Verified match; scope caveats in ledger |
| `README.md:82` | `results/benchmark_20260924T054939Z.json#/models/claude-fable-5-1/all/correct` | `34` | Verified match; scope caveats in ledger |
| `README.md:82` | `results/benchmark_20260924T054939Z.json#/models/claude-fable-5-1/all/n` | `48` | Verified match; scope caveats in ledger |
| `README.md:83` | `results/model_card.json#/benchmark/always_no/correct` | `24` | Verified match; scope caveats in ledger |
| `README.md:83` | `results/model_card.json#/benchmark/always_no/n` | `48` | Verified match; scope caveats in ledger |
| `README.md:84` | `results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/without_plants/correct` | `31` | Verified match; scope caveats in ledger |
| `README.md:84` | `results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/without_plants/n` | `36` | Verified match; scope caveats in ledger |
| `README.md:84` | `results/model_card.json#/benchmark/models/claude-sonnet-5/without_plants/correct` | `33` | Verified match; scope caveats in ledger |
| `README.md:84` | `results/model_card.json#/benchmark/models/claude-sonnet-5/without_plants/n` | `36` | Verified match; scope caveats in ledger |
| `README.md:84` | `results/model_card.json#/benchmark/models/claude-opus-5-5/without_plants/correct` | `33` | Verified match; scope caveats in ledger |
| `README.md:84` | `results/model_card.json#/benchmark/models/claude-opus-5-5/without_plants/n` | `36` | Verified match; scope caveats in ledger |
| `README.md:84` | `results/model_card.json#/benchmark/models/claude-fable-5-1/without_plants/correct` | `34` | Verified match; scope caveats in ledger |
| `README.md:84` | `results/model_card.json#/benchmark/models/claude-fable-5-1/without_plants/n` | `36` | Verified match; scope caveats in ledger |
| `README.md:86` | `results/footage_latest.json#/agreement/artificial_bank/pairs/claude-haiku-4-5-20251001 vs claude-fable-5-1/agree` | `41` | Verified match; scope caveats in ledger |
| `README.md:86` | `results/footage_latest.json#/agreement/artificial_bank/frames` | `46` | Verified match; scope caveats in ledger |
| `README.md:86` | `results/footage_latest.json#/agreement/dug_out_channel/pairs/claude-haiku-4-5-20251001 vs claude-fable-5-1/agree` | `15` | Verified match; scope caveats in ledger |
| `README.md:86` | `results/footage_latest.json#/agreement/invasive_plant/pairs/claude-haiku-4-5-20251001 vs claude-fable-5-1/agree` | `38` | Verified match; scope caveats in ledger |
| `README.md:86` | `results/footage_latest.json#/agreement/pipe_running/pairs/claude-haiku-4-5-20251001 vs claude-fable-5-1/agree` | `30` | Verified match; scope caveats in ledger |
| `README.md:87` | `results/footage_latest.json#/gate/dropped` | `29` | Verified match; scope caveats in ledger |
| `README.md:87` | `results/footage_latest.json#/gate/candidates` | `64` | Verified match; scope caveats in ledger |
| `README.md:87` | `results/footage_latest.json#/gate/kept` | `35` | Verified match; scope caveats in ledger |
| `README.md:88` | `results/model_card.json#/cost/footage_cents_per_call/claude-haiku-4-5-20251001` | `0.22` | Verified match; scope caveats in ledger |
| `README.md:88` | `results/model_card.json#/cost/footage_cents_per_call/claude-sonnet-5` | `0.43` | Verified match; scope caveats in ledger |
| `README.md:88` | `results/model_card.json#/cost/footage_cents_per_call/claude-opus-5-5` | `0.96` | Verified match; scope caveats in ledger |
| `README.md:88` | `results/model_card.json#/cost/footage_cents_per_call/claude-fable-5-1` | `2.32` | Verified match; scope caveats in ledger |
| `README.md:89` | `results/footage_latest.json#/cost/per_100_frames_usd` | `51.2597` | Verified match; scope caveats in ledger |
| `README.md:90` | `results/precache_budget.json#/megabytes` | `2.3` | Verified match; scope caveats in ledger |
| `README.md:90` | `results/precache_budget.json#/files` | `59` | Verified match; scope caveats in ledger |
| `README.md:90` | `results/precache_budget.json#/budget_megabytes` | `3` | Verified match; scope caveats in ledger |
| `README.md:90` | `results/precache_budget.json#/photos/files` | `38` | Verified match; scope caveats in ledger |
| `README.md:96` | `results/model_pass_table.json#/models/claude-haiku-4-5-20251001/artificial_bank/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:96` | `results/model_pass_table.json#/models/claude-haiku-4-5-20251001/dug_out_channel/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:96` | `results/model_pass_table.json#/models/claude-haiku-4-5-20251001/invasive_plant/passed` | `false` | Verified match; scope caveats in ledger |
| `README.md:96` | `results/model_pass_table.json#/models/claude-haiku-4-5-20251001/pipe_running/passed` | `false` | Verified match; scope caveats in ledger |
| `README.md:97` | `results/model_pass_table.json#/models/claude-sonnet-5/artificial_bank/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:97` | `results/model_pass_table.json#/models/claude-sonnet-5/dug_out_channel/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:97` | `results/model_pass_table.json#/models/claude-sonnet-5/invasive_plant/passed` | `false` | Verified match; scope caveats in ledger |
| `README.md:97` | `results/model_pass_table.json#/models/claude-sonnet-5/pipe_running/passed` | `false` | Verified match; scope caveats in ledger |
| `README.md:98` | `results/model_pass_table.json#/models/claude-opus-5-5/artificial_bank/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:98` | `results/model_pass_table.json#/models/claude-opus-5-5/dug_out_channel/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:98` | `results/model_pass_table.json#/models/claude-opus-5-5/invasive_plant/passed` | `false` | Verified match; scope caveats in ledger |
| `README.md:98` | `results/model_pass_table.json#/models/claude-opus-5-5/pipe_running/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:99` | `results/model_pass_table.json#/models/claude-fable-5-1/artificial_bank/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:99` | `results/model_pass_table.json#/models/claude-fable-5-1/dug_out_channel/passed` | `false` | Verified match; scope caveats in ledger |
| `README.md:99` | `results/model_pass_table.json#/models/claude-fable-5-1/invasive_plant/passed` | `false` | Verified match; scope caveats in ledger |
| `README.md:99` | `results/model_pass_table.json#/models/claude-fable-5-1/pipe_running/passed` | `true` | Verified match; scope caveats in ledger |
| `README.md:103` | `results/footage_pool.json#/walks` | `3` | Verified match; scope caveats in ledger |
| `README.md:103` | `results/footage_pool.json#/walk_country_count` | `3` | Verified match; scope caveats in ledger |
| `README.md:103` | `results/fhir_validation.json#/files_validated` | `17` | Verified match; scope caveats in ledger |
| `README.md:103` | `results/fhir_validation.json#/walk_records_validated` | `3` | Verified match; scope caveats in ledger |
| `README.md:103` | `results/fhir_validation.json#/errors` | `0` | Verified match; scope caveats in ledger |
| `README.md:107` | `results/usability_20260929.json#/plan/data_lock_utc` | `"2026-09-28T01:00:00Z"` | Verified match; scope caveats in ledger |
| `README.md:107` | `results/usability_20260929.json#/counts/completed_trained` | `0` | Verified match; scope caveats in ledger |
| `README.md:107` | `results/usability_20260929.json#/counts/completed_untrained` | `0` | Verified match; scope caveats in ledger |
| `README.md:112` | `results/assist_20260929.json#/primary/n_assisted` | `0` | Verified match; scope caveats in ledger |
| `README.md:112` | `results/assist_20260929.json#/primary/n_unassisted` | `0` | Verified match; scope caveats in ledger |
| `README.md:117` | `results/wave2_window.json#/open_utc` | `"2026-09-30T04:00:00Z"` | Verified match; scope caveats in ledger |
| `README.md:117` | `results/wave2_window.json#/lock_utc` | `"2026-10-03T04:00:00Z"` | Verified match; scope caveats in ledger |
| `README.md:117` | `results/wave2_window.json#/lock_local` | `"Friday Oct 2, 2026 at 21:00 PDT"` | Verified match; scope caveats in ledger |
| `README.md:127` | `results/screens.json#/screen_count` | `34` | Verified match; scope caveats in ledger |
| `README.md:127` | `results/screens.json#/phone/css_width` | `390` | Verified match; scope caveats in ledger |
| `README.md:127` | `results/screens.json#/phone/css_height` | `844` | Verified match; scope caveats in ledger |
| `README.md:127` | `results/screens.json#/live_count` | `25` | Verified match; scope caveats in ledger |
| `README.md:127` | `results/screens.json#/local_mock_count` | `9` | Verified match; scope caveats in ledger |
| `README.md:179` | `results/fhir_validation.json#/files_validated` | `17` | Verified match; scope caveats in ledger |
| `README.md:205` | `results/footage_latest.json#/gate/dropped` | `29` | Verified match; scope caveats in ledger |
| `README.md:205` | `results/footage_latest.json#/gate/candidates` | `64` | Verified match; scope caveats in ledger |
| `README.md:210` | `results/footage_pool.json#/walks_with_a_checker_question` | `0` | Verified match; scope caveats in ledger |
| `README.md:210` | `results/footage_pool.json#/walks` | `3` | Verified match; scope caveats in ledger |
| `README.md:438` | `results/precache_budget.json#/megabytes` | `2.3` | Verified match; scope caveats in ledger |
| `README.md:442` | `results/fhir_validation.json#/validator_version` | `"6.10.4"` | Verified match; scope caveats in ledger |
| `README.md:457` | `results/api_inventory.json#/worker/count` | `35` | Verified match; scope caveats in ledger |
| `README.md:457` | `results/api_inventory.json#/python/count` | `29` | Verified match; scope caveats in ledger |
| `README.md:476` | `results/api_inventory.json#/mcp/count` | `5` | Verified match; scope caveats in ledger |
| `README.md:560` | `results/wave2_window.json#/open_utc` | `"2026-09-30T04:00:00Z"` | Verified match; scope caveats in ledger |
| `README.md:560` | `results/wave2_window.json#/lock_utc` | `"2026-10-03T04:00:00Z"` | Verified match; scope caveats in ledger |
| `README.md:568` | `results/test_counts.json#/python/tests` | `2637` | Verified match; scope caveats in ledger |
| `README.md:569` | `results/test_counts.json#/worker_golden/cases` | `282` | Verified match; scope caveats in ledger |
| `README.md:569` | `results/test_counts.json#/worker_golden/node_tests` | `27` | Verified match; scope caveats in ledger |
| `README.md:570` | `results/test_counts.json#/playwright/tests` | `258` | Verified match; scope caveats in ledger |
| `README.md:570` | `results/test_counts.json#/playwright/spec_files` | `33` | Verified match; scope caveats in ledger |
| `README.md:571` | `results/test_counts.json#/worker_e2e/sections` | `19` | Verified match; scope caveats in ledger |
| `README.md:572` | `results/fhir_validation.json#/errors` | `0` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/by_name/gate/killed` | `226` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/by_name/gate/mutants` | `229` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/by_name/followups/killed` | `336` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/by_name/followups/mutants` | `341` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/by_name/scoring/killed` | `53` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/by_name/scoring/mutants` | `53` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/by_name/fhir_emit/killed` | `1678` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/by_name/fhir_emit/mutants` | `1752` | Verified match; scope caveats in ledger |
| `README.md:573` | `results/mutation.json#/threshold_percent` | `85.0` | Verified match; scope caveats in ledger |
| `README.md:600` | `results/wave2_window.json#/lock_utc` | `"2026-10-03T04:00:00Z"` | Verified match; scope caveats in ledger |
| `README.md:615` | `results/judge_check.json#/commit` | `"473ae2c"` | Verified match; scope caveats in ledger |
| `README.md:615` | `results/judge_check.json#/seconds` | `250` | Verified match; scope caveats in ledger |
| `README.md:654` | `results/wave2_window.json#/lock_local` | `"Friday Oct 2, 2026 at 21:00 PDT"` | Verified match; scope caveats in ledger |
| `README.md:677` | `results/wave2_window.json#/lock_local` | `"Friday Oct 2, 2026 at 21:00 PDT"` | Verified match; scope caveats in ledger |
| `README.md:716` | `results/assist_flags.json#/n_flags` | `6` | Verified match; scope caveats in ledger |
| `README.md:718` | `results/consensus_coarseness.json#/summary/at_headline_size/n_patterns_where_feature_only_clearly_loses` | `5` | Verified match; scope caveats in ledger |
| `README.md:722` | `results/footage_latest.json#/gate/kept` | `35` | Verified match; scope caveats in ledger |
| `README.md:722` | `results/model_card.json#/footage_kept/by_feature/dug_out_channel` | `32` | Verified match; scope caveats in ledger |
| `README.md:722` | `results/model_card.json#/footage_kept/by_feature/artificial_bank` | `3` | Verified match; scope caveats in ledger |
| `README.md:726` | `results/wave2_window.json#/lock_local` | `"Friday Oct 2, 2026 at 21:00 PDT"` | Verified match; scope caveats in ledger |
| `README.md:744` | `results/report_pdf.json#/pages` | `9` | Verified match; scope caveats in ledger |
| `docs/devpost.md:46` | `results/fhir_validation.json#/errors` | `0` | Verified match; scope caveats in ledger |
| `docs/devpost.md:70` | `results/fhir_validation.json#/errors` | `0` | Verified match; scope caveats in ledger |
| `docs/devpost.md:71` | `results/footage_pool.json#/frames_kept` | `46` | Verified match; scope caveats in ledger |
| `docs/devpost.md:72` | `results/footage_pool.json#/videos_kept` | `5` | Verified match; scope caveats in ledger |
| `docs/devpost.md:73` | `results/footage_pool.json#/countries_kept` | `3` | Verified match; scope caveats in ledger |
| `docs/devpost.md:74` | `results/footage_latest.json#/gate/dropped` | `29` | Verified match; scope caveats in ledger |
| `docs/devpost.md:75` | `results/footage_latest.json#/gate/candidates` | `64` | Verified match; scope caveats in ledger |
| `docs/devpost.md:76` | `results/benchmark_20260924T054939Z.json#/pool/n_photos` | `16` | Verified match; scope caveats in ledger |
| `docs/devpost.md:91` | `results/footage_pool.json#/walks` | `3` | Verified match; scope caveats in ledger |
| `docs/devpost.md:92` | `results/footage_pool.json#/walk_country_count` | `3` | Verified match; scope caveats in ledger |
| `docs/devpost.md:93` | `results/benchmark_20260924T054939Z.json#/pool/n_photos` | `16` | Verified match; scope caveats in ledger |
| `docs/submission/JUDGE_QA.md:28` | `results/fhir_validation.json#/errors` | `0` | Verified match; scope caveats in ledger |
| `docs/submission/JUDGE_QA.md:50` | `results/model_pass_table.json#/real` | `true` | Verified match; scope caveats in ledger |
| `WRITEUP.md:28` | `results/footage_latest.json#/gate/dropped` | `29` | Verified match; scope caveats in ledger |
| `WRITEUP.md:29` | `results/footage_latest.json#/gate/candidates` | `64` | Verified match; scope caveats in ledger |
| `WRITEUP.md:30` | `results/footage_latest.json#/gate/kept` | `35` | Verified match; scope caveats in ledger |
| `WRITEUP.md:67` | `results/test_counts.json#/worker_golden/cases` | `282` | Verified match; scope caveats in ledger |
| `WRITEUP.md:68` | `results/test_counts.json#/worker_golden/files` | `9` | Verified match; scope caveats in ledger |
| `WRITEUP.md:69` | `results/test_counts.json#/worker_golden/node_tests` | `27` | Verified match; scope caveats in ledger |
| `WRITEUP.md:77` | `results/fhir_validation.json#/errors` | `0` | Verified match; scope caveats in ledger |
| `WRITEUP.md:78` | `results/fhir_validation.json#/files_validated` | `17` | Verified match; scope caveats in ledger |
| `WRITEUP.md:139` | `results/model_sweep_20260924T030451Z.json#/counts/malformed` | `73` | Verified match; scope caveats in ledger |
| `WRITEUP.md:140` | `results/model_sweep_20260924T030451Z.json#/counts/answers` | `144` | Verified match; scope caveats in ledger |
| `WRITEUP.md:146` | `results/model_sweep_20260924T031128Z.json#/counts/malformed` | `0` | Verified match; scope caveats in ledger |
| `WRITEUP.md:147` | `results/model_sweep_20260924T031128Z.json#/counts/answers` | `144` | Verified match; scope caveats in ledger |
| `WRITEUP.md:189` | `results/warmup_photos.json#/runs/before/dpr/2/median_photo_bytes` | `1459038` | Verified match; scope caveats in ledger |
| `WRITEUP.md:190` | `results/warmup_photos.json#/runs/after/dpr/2/median_photo_bytes` | `253409` | Verified match; scope caveats in ledger |
| `WRITEUP.md:191` | `results/warmup_photos.json#/runs/before/dpr/2/median_load_ms` | `8445` | Verified match; scope caveats in ledger |
| `WRITEUP.md:192` | `results/warmup_photos.json#/runs/after/dpr/2/median_load_ms` | `2504` | Verified match; scope caveats in ledger |
| `README.md:617` | `results/judge_check.json` rendered judge-check block | Whole saved block matches its source | Verified historical match; current run is blocked as recorded above |
