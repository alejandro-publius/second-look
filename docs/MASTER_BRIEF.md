# Second Look: master prompt for Claude Code

This one file replaces the earlier rung 1 brief and the three-file kickoff package. Where they disagree with this file, this file wins.

## 0. How Alex uses this file

1. Create a private GitHub repo called `second-look` with an MIT license. Save this file as `docs/MASTER_BRIEF.md`. If you have them, add `fhir/citizen_followercity_spike.fsh` and `scripts/sandbox_write_test.sh` from the planning chats.
2. Start Claude Code in plan mode: `claude --permission-mode plan`.
3. Send: "Read docs/MASTER_BRIEF.md from top to bottom, then do what section 17 asks."
4. Every later session starts fresh with: "Read CLAUDE.md and PLAN.md, then run Session <letter> from section 15 of docs/MASTER_BRIEF.md."

Everything below is addressed to Claude Code.

## 1. What this project does

One sentence: Second Look spends two minutes teaching and testing a volunteer on the creek damage people usually miss, then saves their score with every observation they make, so a city knows how much to trust it.

The idea in plain words:

- People judge a creek the way they judge a park. Tidy and green reads as healthy. OneAquaHealth's project lead said it from the other side in the first workshop: volunteers catch smell, foam and colour, and walk past concrete banks, a channel that was dug out, and pretty plants that do not belong. So the best-looking creek can get the best rating and deserve the worst.
- Professional river surveyors solved this in the 1990s with a test. In the UK's River Habitat Survey, a surveyor's data is not entered until they have trained and passed an accreditation test, and one certification runs out after three years. The project lead will know the method. It has been run at more than 700 sites in Portugal.
- Second Look is the two-minute version of that test for volunteers. You look at creek photos with known answers. You learn the four things people miss, and the app learns how good you are at each one. That score is saved with every observation you later make at a creek, in OneAquaHealth's own FHIR format.
- OneAquaHealth says citizen data should have the same standing as lab data. A lab result is trusted because its quality checks travel with it. This gives a volunteer's result the same thing.
- AI takes the same test as the people. A vision model may raise a flag only on a feature where it passed, the flag can only become a question to the volunteer, and the volunteer always answers first.
- We check the lesson on strangers. Half get the two minutes, half do not, everyone judges the same 16 photos, and the counting rules are published before anyone takes it.

Three people use it:

- The volunteer: takes the lesson and the test once, then does a guided check at a creek, and a 20 second quick check on later visits.
- The city analyst: reads a creek's record and sees, next to each answer, how the person who gave it scored on that exact feature.
- The judge: opens the demo link, takes the two-minute test, and sees their own score beside the untrained and trained averages.

## 2. The event and how it is judged

- OneAquaHealth IEEE Global Hackathon 2026. Build window Sep 16 to 30. Hard deadline Sep 30 at 9:00pm PDT. We do a full dry-run submission on Mon Sep 28 and submit by 6:00pm on Sep 30. The live demo must stay up through Oct 15.
- Track: Track 3, AI-Supported Assessment. Its problem line is "Citizen observations can be inconsistent and error-prone" and its build list is AI prompts, validation checks, explainable AI and human-in-the-loop workflows. This holds only if the model run in Session C ships. If it slips, we enter Track 1, Citizen Science UX, whose build list (guided workflows, simplified ecological terms, improved data accuracy, repeat engagement) matches rungs 1 and 2. Prizes are overall, not per track.
- Rubric, each scored 1 to 10:
  - Impact and alignment with the OneAquaHealth mission, 30%: improves monitoring, protection, awareness or sustainability of water ecosystems and their connection to human, animal and environmental health.
  - Innovation and creativity, 20%: originality, and creative use of technology on ecosystem and citizen science challenges.
  - Technical implementation, 20%: quality of prototype, architecture and functionality, and effective use of tools, APIs or data sources.
  - Usability and user experience, 15%: ease of use, clarity of interface, and accessibility for intended users.
  - Feasibility and scalability, 15%: real-world implementation, scalability, and integration with existing systems.
- The organizers' email of Sep 20 says a submission must clearly show five things. Use them as the README and Devpost headers: the problem; how the solution aligns with OneAquaHealth; innovation and practical value; effective use of data, technology, AI, APIs and standards; a clear demonstration of what was built.
- Ten judges, minutes per entry. Half are from the OneAquaHealth consortium (a freshwater ecologist who leads the project, the company behind their data tools, digital health and outreach people). Half are IEEE standards and engineering people (an HL7 fellow who advises at UC Berkeley, an integration program manager who works with agents and MCP, two from the IEEE blockchain community). Last year the same organizers gave three first prizes to simple, honest projects with working demos and reported results. The first screen and the first minute of video carry the score.

## 3. What the workshops said that the build must reflect

- Workshop 1, project lead: the three things volunteers miss; the app's overall rating is somewhat subjective and better informed after the earlier questions; the app ends by asking how the person feels at the stream, so keep that question; the app works anywhere in the world; restoring urban streams is a public health measure; her decision tool answers with measures such as replanting margins, fixing sewers, reconnecting floodplains and removing barriers; a site can rate bad on one thing and good on another, so show each check instead of one blended grade.
- Workshop 1, hackathon co-lead: creativity first; scale the European work across the globe; any data is allowed; AI on app photos is welcome; a missing demo video can mean rejection; entries are shown on their hub and they collect waivers.
- Workshop 2, a stream ecologist: a tool that makes the stream less necessary has failed; technology belongs embedded in nature; one visit is a snapshot, repeated visits make a story; rivers flow one way, so upstream matters.
- Workshop 3: their One Digital Health template is a story, a score on five dimensions (citizen engagement, education, human and veterinary healthcare, industry 4.0, environment) and a FAIR level. The write-up gets a short box with exactly that.
- Workshop 4: builds are expected to use FHIR; citizen observations share the same profiles, value sets and validation rules as lab data and are traceable to the contributor, and they called this a key innovation; the implementation guide has no citizen example; do not exchange the logical models, validate real resources against the profiles with the package; Locations nest with partOf; the Location profile can point at a form; units follow UCUM; the sandbox is there to be read and written; a new city that adopts the method is called a follower city, and there is a five-step recipe for it; their roadmap names environmental DNA and microbial metagenomics, which is Rachel's field.
- The official app, from its public text (Alex confirms against his own screenshots): no training, no quiz, no AI wording. It asks "Is more than one third of the left margin covered by impervious areas (such as roads, sidewalks or buildings)?", offers bank types including "Artificial (concrete or stones with concrete)", asks "Do you see any non-native or invasive plant species?", "Are there pipes draining polluted water into the stream?" and "Is there any kind of water entry or discharge of sewage?". No question covers a dug-out channel. That idea appears only inside the overall rating, whose best option mentions a natural channel and whose worst says highly modified. Their Community site hosts training materials, so we never claim that no training exists. Ours is two minutes, inside the flow, tested on strangers, and the score travels with the data.

## 4. Hard rules

1. New code only. Everything is written inside the build window in this repo. Never copy or adapt code from earlier projects of Alex's (Last Elevator, Tideline, Project Blackbox), even if you find it on disk or he pastes it by mistake. The spike file and the sandbox script were written on Sep 20 for this event and may be used. List open source dependencies with licenses in `docs/THIRD_PARTY.md`. The README has a "How this was built" section that says plainly what AI coding tools did and what the two humans did.
2. The model never decides. Model output is parsed into a list of `Flag` objects or rejected. A flag can do exactly one thing: make one follow-up question eligible. A model never sets a label, never names or creates a site, never writes or edits an answer. Enforced in two places: the record builder accepts human answers only (no parameter carries model output), and `core/gate.py` rejects anything that is not a valid flag. A fuzz test proves that for any model output the stored answers equal the human answers and every computed label equals the function of human answers alone. Any change to the gate needs a test in the same commit. The gate and its fuzz test exist from the first session, before any model is wired in.
3. Code decides the questions. Follow-up selection is a pure function of answers, site context, the volunteer's scores and flags. Two follow-ups at most. No model call inside it.
4. A model earns its flags. A model may flag a feature only if it passed the same test as the volunteers on that feature (section 8). The pass table is a committed file that the gate reads.
5. Approved sentences. Every health or ecology statement a user sees comes from `content/approved_sentences.yaml`, each with a source. Code picks among them by id. No model writes user-facing claims. The only model text a user ever sees is a flag's short note, labelled "the checker noticed", never stated as fact. No sentence about health ships until Rachel has read the OneAquaHealth indicator factsheets and approved it. Nothing we show states a risk for a specific site.
6. Real photos only. Own photos or open licenses (CC0, CC BY, CC BY-SA, public domain). No AI-generated or AI-edited images anywhere, placeholders included: use labelled gray blocks until real photos land. No faces, house numbers or licence plates. Every image has a row in `photos/manifest.csv`. No row, no photo. CI enforces it.
7. The usability test is anonymous. Adults only, consent before anything else, no names, no emails, no IP addresses stored or logged by our code, no free-text fields, no third-party analytics, fonts or scripts, no fingerprinting. Identifiers are a random session id and a hashed random browser token. Write down in `docs/DATA_HANDLING.md` what the hosting provider logs on its own, and make the consent text match.
8. Field use is pseudonymous. No accounts. A random contributor token. Strip EXIF on upload. One visitor never sees another visitor's upload. Uploads auto-delete after 30 days. Coarse location unless the user places the pin.
9. Their systems. No calls to `api.enora-oah.eu` until Alex says permission arrived. If it never arrives, we ship without their data. Never call an endpoint that needs credentials. Never commit their raw data: commit the fetch script, a dated manifest with hashes, and derived numbers only. `data/raw/` is gitignored.
10. Their sandbox, `https://sandbox.hl7europe.eu/oneaquahealth/fhir`, is shared by every team and allows delete and `$expunge`. Our own store of validated FHIR JSON is the source of truth. The sandbox is a mirror. Conditional creates only. Never delete by search. Never `$expunge`. Delete only ids recorded in `fhir/sandbox_ledger.jsonl`. Keep `scripts/repush_sandbox.py` working at all times. Every resource we write carries our `meta.tag`.
11. FHIR. R4 (4.0.1). The implementation guide is pinned to `hl7-eu/oah` commit `b907cf0`, recorded in `fhir/ig.lock` with the package sha256. Build the package from source with SUSHI. Every emitted resource is validated in CI with the HL7 validator plus that package. Python FHIR libraries often default to R5, so use an R4 compatible module and let the validator be the judge.
12. Claims. Every reported result in `README.md` or `docs/` (this brief and other planning files in `docs/` excluded by path) is produced by a script in `evals/` that writes to `results/`. `scripts/verify_claims.py` parses the README and checks each number. It runs in CI. Failed cases are committed beside successes. Never hand-edit a number.
13. Pre-specified analysis. `docs/analysis_plan.md` (section 7) is committed and tagged `prereg-v1` before the first real participant. The analysis script refuses to read real outcomes before data lock, and refuses to run at all if the tag is missing or the plan file differs from the tagged version. Before lock, monitoring prints counts per arm and nothing else. Changes after the tag go in `docs/deviations.md` with a date and a reason, and the README shows the deviation count.
14. No secrets in the repo. `.env.example` only.
15. The repo stays private until submission day, then goes public before the final incognito check. Small commits with honest messages. Never rewrite history, squash or backdate. The commit timeline is evidence that the work happened inside the window.
16. Licenses. Code is MIT. Our own photos and copy are CC BY 4.0. The README states both.
17. Accessibility is part of the score: WCAG 2.2 AA, keyboard reachable, labelled controls, 4.5 to 1 contrast, large tap targets, readable in sunlight, alt text that describes the scene without giving away a test answer.
18. How we write. Plain words, reading age about 12, like a person explaining it to a neighbour. Concrete nouns and verbs: who did what, and what happened. No filler and no hype: never "real number", "seamless", "robust", "leverage", "cutting-edge", "empower", "unlock", "first-of-its-kind". If a sentence could sit in any project's README, delete it or make it specific. No em dashes or en dashes anywhere in the repo, including UI copy, docs and commit messages.
19. Working style. Recommend one path and give the reason in a line. No option menus. At most one plain question at a time. Every milestone ends with a command that proves it, and you show the output. If stuck for more than 15 minutes, stop and say what you tried and what you recommend. Prefer deleting scope to adding complexity. If a rung is at risk, finish the rung below it first.

## 5. Stack, layout, commands

- Web: Next.js (App Router) PWA, TypeScript, mobile first. Works on desktop with sample photos so judges need no camera. All UI strings live in a locale file, English only for now.
- API: FastAPI, Python 3.12 or newer, Pydantic, SQLModel. SQLite locally, Postgres in production through `DATABASE_URL`.
- Analysis and evals: Python with numpy, scipy, pandas, and DuckDB over exported CSV or Parquet. DuckDB is never the live write store.
- Core logic: pure Python in `core/` with no I/O.
- Models: read model ids from config. Defaults for the test run are `claude-haiku-4-5-20251001`, `claude-sonnet-5` and `claude-opus-5`. Confirm them against the models page before the first paid run. Batch API for evals. Resize photos to 1092 px on the long side. Log every call to `results/cost_log.jsonl` (model, tokens, cost, purpose). Keep `ANTHROPIC_API_KEY` out of any shell where Claude Code itself runs on a subscription.
- FHIR: FSH sources in `fhir/`, emitter in `core/fhir_emit.py`, HL7 `validator_cli.jar` in CI.
- Rainfall: a free global source such as Open-Meteo. Check its terms, attribute it, cache responses.
- Hosting: must stay up through Oct 15 at little or no cost. Recommend one host in PLAN.md. A self-hosted HAPI server is optional, not required.

```
apps/web/        Next.js PWA
apps/api/        FastAPI app
core/            rules, follow-up selector, gate, labels, fhir_emit (pure functions)
content/         lessons, test items, form schema, follow-ups, glossary, approved sentences, regions/, locales/
photos/          manifest.csv and image files
evals/           scripts that produce every reported number
results/         outputs of evals, committed, failures included
scripts/         verify_claims.py, preflight.py, freeze_key.py, repush_sandbox.py, sandbox_write_test.sh
fhir/            ig.lock, FSH, sandbox_ledger.jsonl, postman/
docs/            MASTER_BRIEF.md, analysis_plan.md, deviations.md, fhir_mapping.md, DATA_HANDLING.md, THIRD_PARTY.md, DECISIONS.md, notes/
```

`make dev` runs everything locally. `make check` runs lint, type checks, pytest, the web build, the photo manifest check, FHIR validation and verify_claims. It must pass before every commit to main. `make preflight` is the launch gate in section 6.

## 6. Rung 1: the lesson, the test, and the check on strangers

Content, all of it data so Rachel can edit without touching code:

- `content/features.yaml`: four features with id, plain name, one-line rule of thumb, and the question asked in the test.
  - `artificial_bank`: concrete walls and other built banks. Question uses the app's own wording where possible.
  - `dug_out_channel`: a channel that was deepened or straightened. The app has no such question, so this wording is ours. It supports the overall rating.
  - `invasive_plant`: pretty plants that do not belong here. Question uses the app's wording.
  - `pipe_running`: pipes and sewage signs. The lesson teaches one rule: a pipe still running after three dry days is worth a second look. Question uses the app's wording.
- Items have stable ids. They become FHIR Questionnaire linkIds in rung 2. Each carries `app_item` (which app question it mirrors, if any) and `verified_against_app` (true only after Alex checks his screenshots). Never move guessed wording into a verified state.
- `content/lessons/<feature>.yaml`: two contrast pairs (what people assume beside what is there), the rule of thumb, one practice photo with feedback that names the cue. 25 words a screen at most.
- Invasive plants depend on the region. Species examples live in `content/regions/<region>.yaml`. Ship `california-bay-area`. General cues stay global. A species name appears only on a photo Rachel has verified, with a source.
- `photos/manifest.csv` columns: id, file, sha256, source_url, author, license, capture_date, coarse_location, scene_id, role (warmup, lesson, practice, test, benchmark), feature, gold_label (present, absent, ambiguous), labeller_2, synthetic (always false), faces (always false), notes. Design it once. The rung 3 benchmark reuses it.
- The loader fails loudly if: a photo has no manifest row or a wrong hash; a license is not on the allowlist; a lesson or practice photo shares a hash or a scene_id with a test photo (the same spot on the same day is one scene); a test item is labelled ambiguous; the test set is not 16 items with 2 present and 2 absent per feature.

The flow, mobile first, no login:

1. Landing and consent: what this is (a usability test of a training tool), about 4 minutes, anonymous, adults only, quit any time, exactly what is stored, no health advice, contact email. Two checkboxes (consent, 18 or older). The consent text is version-stamped. Each session stores the consent version, the content hash and the build hash.
2. Warm-up, before anyone is assigned: two creek photos side by side and one question, "Which creek is healthier?" No feedback. Reported as a description only.
3. Assignment: server side, permuted blocks of 4, from a stored seed. The browser cannot pick its arm or learn about the other one. Write the allocator for k arms, because a third arm may come later.
4. Trained arm: the lesson first. Four cards, one per feature. A visible progress bar. Record lesson seconds per screen.
5. The test: 16 photos, one question each, buttons Yes, No, Can't tell. A glossary tooltip on the key term. No feedback during the test. Order shuffled per participant with the seed stored.
6. Untrained arm: the test first, then the lesson is offered as a thank you. Nothing after that point is analysed.
7. End screen: the person's score per feature, a share link, and one optional question, "Have you ever assessed a stream before?" Per-photo answers stay hidden until the test closes, so they cannot be passed along.
8. First screen line: this trains your eyes for the visit and never replaces going. Last screen line: one visit is a snapshot, repeated visits make a story. Rachel owns the wording.
9. `/demo` walks a judge through the lesson and the test without writing to the study tables, then shows their score beside the untrained and trained averages once those exist.
10. QA sessions carry an `is_test` flag set by a secret key and are excluded. The table is wiped at launch and the wipe is logged in `docs/deviations.md`.

API: tables `session` (id, arm, block_id, item_order, consent_version, content_hash, build_hash, consent_at, started_at, lesson_seconds, completed_at, client_token_hash, ua_class, is_test) and `response` (session_id, item_id, answer, rt_ms, position). Endpoints: `POST /api/test/session`, `POST /api/test/response` (idempotent), `POST /api/test/lesson-done`, `POST /api/test/complete`, `GET /api/test/export` (token protected, anonymous CSVs), `GET /api/test/counts` (counts per arm only).

Launch gate, `make preflight`, fails closed and prints every failed check: loader checks pass; every item has `verified_against_app` true or is marked as our own wording; two independent labels exist for every test photo and Cohen's kappa is written to `results/key_agreement.json`; `scripts/freeze_key.py` has written the key hash; consent appears before assignment (end-to-end test); no request goes to a third-party origin (end-to-end test on the network log) and our server logs carry no IP (test); the `prereg-v1` tag exists and matches; analysis tests pass; verify_claims passes; the automated accessibility check reports no serious violations.

## 7. The pre-specified analysis plan

Write the text below to `docs/analysis_plan.md` word for word, keeping the TODO lines. It becomes binding when tagged `prereg-v1`.

> **Pre-specified analysis plan: Second Look usability test**
>
> This is a usability test of our own tool, run to improve it and to report honestly how well it works. Participation is anonymous and voluntary. We collect no names, emails, IP addresses or precise locations. It is not designed or presented as generalizable human-subjects research.
>
> 1. Question. Does a two-minute photo lesson help untrained adults recognise four stream features that volunteer assessors commonly miss: artificial banks, a dug-out channel, invasive plants, and pipes or sewage signs? Source for the choice of features: the OneAquaHealth project lead, hackathon workshop 1.
> 2. Design. Two arms, randomized 1 to 1 in permuted blocks of 4, assigned by the server from a stored seed. Trained: lesson, then test. Untrained: test, then the lesson is offered afterwards. Participants are adults who open the public link. No screening beyond the consent and age checkboxes.
> 3. Materials. 16 test items. Each pairs one photo with one feature and one question. Answers: Yes, No, Can't tell. 4 items per feature, 2 present and 2 absent. Order randomized per participant. Gold labels are set by Rachel Selbrede, blind to any model output, from written definitions. A second labeller (Alex Velazquez) labels every test photo independently. We report Cohen's kappa. Photos either labeller calls ambiguous are removed before launch. No photo, and no photo from the same spot on the same day, appears in both the lesson and the test. Exact question wording, frozen before tagging: artificial_bank TODO-RACHEL; dug_out_channel TODO-RACHEL; invasive_plant TODO-RACHEL; pipe_running TODO-RACHEL.
> 4. Outcomes. Primary: per-participant accuracy, the share of the 16 items answered correctly, with Can't tell counted as incorrect. Descriptive only, no significance tests: accuracy per feature, hit rate and false-alarm rate per feature, share of Can't tell answers, median test time, median lesson time, accuracy by self-reported prior experience, and the warm-up item (share choosing each photo).
> 5. Exclusions, decided now. Sessions that did not finish all 16 items. Tests completed in under 40 seconds. Repeat visits from the same browser token (only the first completed session counts). Sessions flagged as QA. Dry-run sessions before launch (the table is wiped at launch and the wipe is logged). We report how many sessions each rule removed, and how many were randomized, started and completed in each arm.
> 6. Analysis. Estimate: mean accuracy of the trained arm minus mean accuracy of the untrained arm. Interval: percentile bootstrap, 10,000 resamples, stratified by arm, seed 20260920, 95 percent. Test: two-sided permutation test on the difference in means, 10,000 permutations, alpha 0.05. One confirmatory test. Also reported: Hedges g and the full distribution of scores per arm as a plot. Sensitivity checks: partial completers with unanswered items scored incorrect; excluding people who report prior stream assessment. The code is `evals/usability_analysis.py`, written and tested on synthetic data before launch, including a scenario where people say Yes more often without being more accurate, which must show no gain.
> 7. Sample size and stopping. Target: 80 completed sessions, 40 per arm. Planning note from our own simulation with 16 items and untrained accuracy near 60 percent: about 80 percent power for a 10 point difference at 40 per arm, and for about 12 points at 30 per arm. We make no promise of reaching the target. Data lock is Sunday Sep 27, 2026 at 18:00 PDT whatever the count. Before lock we look at counts per arm only. The confirmatory claim needs at least 20 completed sessions per arm. Below that we report the results as a description and say so.
> 8. People and models on the same test. Each configured vision model answers the same 16 items with the same question wording, three repeat runs, settings recorded. We report each model's accuracy beside the two human arms with a Wilson interval, and say plainly that 16 items is a small set. Pass rule for rung 1, fixed now: a model passes a feature only if it answers all 4 items for that feature correctly in at least 2 of its 3 runs. Only a passed feature may ever produce a flag. The larger benchmark in rung 3 (target 150 photos) replaces this rule with one written into this plan as a dated deviation before that benchmark is run.
> 9. What we publish whatever happens. All results, including no effect or a negative effect, and any model that beats trained people. The anonymous response table at data lock. Exclusion counts, the deviations log and the cost of the model runs.
> 10. Ethics and privacy. Consent screen as described in the repo. Stored: random session id, arm, answers, timings, a hashed random browser token, coarse device class, consent version. Nothing else. Photos contain no faces, house numbers or licence plates.

`evals/make_synthetic_sessions.py` generates three fake data sets: no effect, a real accuracy gain, and a Yes bias with no accuracy gain. Tests assert that the no-effect case rejects about 5 percent of the time, that the real gain is recovered inside its interval, and that the Yes bias shows no gain. `evals/power.py` replaces the planning note with a committed simulation.

## 8. AI takes the same test

- `evals/model_sweep.py`: for each configured model, send the resized photo and the identical question text per test item. Force the answer into yes, no or cant_tell plus a note of at most 160 characters. Three repeat runs. Batch API. Write accuracy, per-feature results, the pass table (`results/model_pass_table.json`) and cost to `results/`.
- The comparison table in the README has four kinds of observer on the same 16 photos: untrained people, trained people, and each model. It answers one question with evidence: where may AI speak, and where should it stay quiet.
- `core/gate.py` reads the pass table. A flag for a feature the model did not pass is dropped and the drop is logged.
- Session A builds the sweep against a fake client only. Session C runs it for real.

## 9. Rung 2: the guided check at the creek and the record

The form:

- `content/form.yaml` mirrors the official app's items in the app's order, with stable ids, from Alex's screenshots. Keep the overall rating and the closing question about how the person feels at the stream. Every item has `verified_against_app`.
- Guided, one question per screen, photos welcome, glossary links on every technical word, works one-handed.

Follow-up questions, chosen by code, two at most, from a fixed priority table in `content/followups.yaml`:

1. Dry pipe. If the volunteer reported a pipe, look up rainfall for the spot. If the past 72 hours had no more than 2.5 mm in total (configurable, source cited), ask: "It has not rained here for N days. Is anything coming out of that pipe?" Cities screen storm drain outlets the same way, in dry weather, because nothing should be running then. Not all dry-weather flow is a problem, so the wording is always "worth testing", never "sewage".
2. Rating check. If the overall rating is the best option and the answers include a built bank, a margin more than one third paved, invasive plants, or a sewage sign, say so and ask whether they want to keep their rating. Store both the first and the final rating. Never change it for them.
3. Checker flag (rung 3 only, and only for a passed feature): "The checker noticed something that may be a built edge on the left bank. Want to look again?"
4. Low score. If the volunteer scored 2 of 4 or lower on a feature and answered No to it, ask for a photo of that feature so a reviewer can check.

What the analyst sees: each answer beside the observer's score on that feature ("4 of 4 on built banks, tested Sep 23") and the result of each check that ran. No blended grade. No probability. A score older than 90 days shows as expired and the volunteer is invited to retake the test.

The health card ends in one action each for the person, the pet and the city. Sentences come only from `content/approved_sentences.yaml`. City actions point at the measures the project lead's decision tool returns: replant margins, fix sewers, reconnect the floodplain, remove barriers. Pets cover the veterinary side of One Digital Health.

Return visits: a saved spot gets a 20 second quick check (colour, smell, is the pipe running, optional photo) and a timeline of every visit.

The record in FHIR. Write `docs/fhir_mapping.md` first, prove it with SUSHI and the HL7 validator, then build. Proposed shape, smallest thing that validates wins:

- Three nested Locations under their Location profile: creek, reach (partOf creek), spot (partOf reach, with position). Each needs an identifier, a name and mode instance. Our creek-check Questionnaire is referenced through the profile's form extension wherever the profile allows it.
- A pseudonymous Practitioner: identifier only, never a name. One qualification: code from our CodeSystem for the Second Look test, period from the test date to 90 days later, issuer our Organization.
- The test as a Questionnaire, and the volunteer's sitting as a QuestionnaireResponse authored by that Practitioner, with per-feature scores computed by code and stored as items.
- The creek check as a Questionnaire whose linkIds are our stable item ids, and one QuestionnaireResponse per visit.
- One Observation per answered item under their Observation profile: status final, code from our local CodeSystem (their binding is preferred, so local codes pass), subject the spot, effectiveDateTime, performer the Practitioner, a coded or quantity value with UCUM units, derivedFrom the visit QuestionnaireResponse.
- One Provenance per visit: targets are the Observations, agents are the Practitioner and our software, entities are the visit QuestionnaireResponse and the test QuestionnaireResponse, so any reader can walk from an answer to the score of the person who gave it.
- A Library in their sandbox that describes our data set and points at our repository. This is their own FAIR pattern: a registry entry with them, the data with us.
- Berkeley is a follower city. Strawberry Creek on the UC Berkeley campus is the worked example.
- Deliver `fhir/postman/second-look.postman_collection.json` that replays create, read and delete with creek records, the same steps the organizers demoed with a Patient.

## 10. Rung 3: the checker that can only ask

- A vision model sees the photo and one feature question. Output goes through the gate. Only passed features. At most one of the two follow-up slots. It never pre-fills and never writes. The person has already answered before any flag is shown.
- Benchmark on the labelled photo pool (target 150, run on whatever is labelled): accuracy per feature per model with intervals, the human agreement ceiling from a 50 photo overlap between the two labellers (Cohen's kappa per feature), and an ablation of rules only, context only, vision only, and all three.
- Adversarial photos (blank frames, indoor scenes, screenshots) must produce no flags or a cant_tell.
- New test photos from this pool rotate into the volunteer test so answers cannot be memorised.

## 11. Rung 4: only if everything above is green

A sampling referral when two different volunteers report the same pipe running in dry weather. A hash-chained audit log over record writes (call it an audit log). A small MCP server over our own records. An upstream pull request to `hl7-eu/oah` with the citizen example. A note on reaches downstream of a finding. A biofilm microbial panel modelled in their profiles, which is Rachel's field and on their roadmap. More languages.

## 12. README and Devpost shape

- First screen: the one sentence, the two warm-up photos, and one table: untrained people, trained people and each model on the same 16 photos, with the number of people. A judge gets the result in 30 seconds.
- Then the five headers from the organizers' email, in their order.
- Then: Try it (demo link, no camera needed), How we know it works (plan tag and hash, participant flow, primary result with its interval, per-feature table, deviation count), Architecture (one diagram in their five pipeline stages: collection, transformation, validation, aggregation, publication), Feasibility as their five replication steps run on Berkeley, a short One Digital Health and FAIR box, Data and photo rights, How this was built, Known weaknesses.
- Use the rubric's own phrases where they are true of us: citizen science challenges; effective use of tools, APIs and data sources; accessibility for intended users; integration with existing systems.
- If the lesson shows no effect, the first screen says so, and the per-feature table says which lesson to fix.

## 13. Schedule

| Day | Session | Ends with |
|---|---|---|
| Sun Sep 20 | A: scaffold, content files, API, analysis on synthetic data, gate, sweep stub | `make check` green in CI |
| Mon Sep 21 | B: lesson, test and demo screens, consent, deploy | a public URL that works on a phone |
| Tue Sep 22 | C: real photos and copy, dry run, preflight, tag, real model run | ready to launch |
| Wed Sep 23 | launch the link in the morning; D: form and follow-ups | responses arriving |
| Thu Sep 24 | light evening, D continues | guided check works end to end |
| Fri Sep 25 | E: FHIR record, validator in CI, sandbox mirror, health card, return visits | a validated record in our store and mirrored |
| Sat Sep 26 | F: checker, benchmark, ablation, accessibility pass | freeze at night |
| Sun Sep 27 | data lock 18:00 PDT; G: run the analysis once, README, Devpost draft | every README number verified |
| Mon Sep 28 | record and edit the video; full dry-run submission | dry run done by midnight |
| Tue Sep 29 | fixes only, after 7pm | |
| Wed Sep 30 | repo public, incognito check, submit by 6:00pm | |

## 14. What the humans supply

- Rachel, by Tue Sep 22 noon: about 40 photos (16 test, 16 for eight contrast pairs, 4 practice, 2 warm-up, spares) following the shot list in section 16; gold labels, blind; one rule of thumb per feature with a source; the Bay Area invasive list checked against the Cal-IPC inventory; approved sentences after reading the indicator factsheets.
- Alex: independent second labels; a Community account, one assessment in the real app with a screenshot of every screen, and a look at the Community's training materials; five lines of notes on OneAquaHealth's ten-minute AI image model video in `docs/notes/their_image_model.md`; the consent contact email; the hosting account; `sandbox_write_test.sh` run once with the repo URL filled in; recruiting from Wednesday through lab and class chats, club servers, friends and family and local creek groups.
- Both: one creek visitor on camera taking the two-minute test, ideally someone who walks a dog there.
- Tell Alex the latest date each input can arrive without moving the launch.

## 15. Session prompts

**Session A.** Goal: backend and analysis for the usability test, with placeholders that are easy to swap. Build in this order: scaffold, Makefile, CI, `.env.example`, README stub with the section 12 headings; content files and manifest with 40 gray placeholder images and the loader checks; the API and allocator from section 6; `evals/usability_analysis.py`, `evals/make_synthetic_sessions.py` and `evals/power.py` from section 7; `evals/model_sweep.py` against a fake client; `core/gate.py` with the `Flag` model (kind, confidence, note up to 160 characters, optional region) and the fuzz test; `scripts/verify_claims.py`; write `docs/analysis_plan.md` from section 7. Tests that must exist and pass: arm balance within blocks; lesson and test photos disjoint by hash and scene; test set composition; idempotent responses; export contains no identifiers; counts endpoint returns counts only; analysis recovers a planted effect, reports none under no effect and none under Yes bias; analysis refuses real data without the tag; gate fuzz test; verify_claims passes on the stub. Do not build tonight: any UI beyond a health page, FHIR, photo upload, the checker, any call to OneAquaHealth systems. Done means `make check` is green locally and in CI, and the synthetic run prints the results table.

**Session B.** Build the flow in section 6 in `apps/web`, including the warm-up, both arms, the end screen and `/demo`. Accessibility pass. Deploy web and API. Playwright tests for both arms on a phone viewport, including the third-party request check.

**Session C.** Swap in real photos and Rachel's copy. Run the loader. Freeze question wording in the plan. Dry run with three friends on their own phones, fix what confuses them, wipe, log the wipe. Run `make preflight`. Commit and tag `prereg-v1`, and give Alex the plan's SHA-256 to post publicly. Run the model sweep for real and commit the results, failures included.

**Session D.** `content/form.yaml` from the screenshots. The guided check UI. The follow-up selector as a pure function with a test for each rule and for the two-question cap. Rainfall lookup with caching and the fixed dry rule. The analyst view of one record.

**Session E.** `docs/fhir_mapping.md`, then FSH, then the emitter. SUSHI and the HL7 validator in CI. Our store. The sandbox mirror with ledger and repush. The Postman collection. The Library entry. The health card. Quick check and timeline.

**Session F.** The checker through the gate, passed features only. The benchmark, agreement and ablation scripts. Adversarial photos. Rotate new photos into the volunteer test. Demo mode polish. Accessibility pass. Freeze.

**Session G.** After data lock: run the analysis once, generate the README table from `results/`, run verify_claims, finish the README in the section 12 shape, write `docs/devpost.md`, draw the architecture diagram.

## 16. Photo shot list for Rachel

Phone, landscape, daylight, standing on the bank, both bank and water in frame. No people, house numbers or plates. Three shots per spot. Keep the originals. Write down the spot and the date. Use Strawberry Creek plus at least two other East Bay creeks, so lesson and test photos never share a spot. For each feature we need clear present, clear absent, and the look-alikes that fool people. Anything you would call ambiguous stays out of the test.

- Built banks. Present: concrete walls, stones set in concrete, a wall hidden under ivy. Absent: natural rock, a raw earth bank that looks messy.
- Dug-out channel. Present: straight reach, even sloped banks, the same width all along, flat slow water, no trees or trees all the same age. Absent: bends, bars, pools, fallen wood, changing width.
- Plants that do not belong. Present: showy single-species stands crowding the bank, checked against the regional list. Absent: native streamside trees and shrubs that look scruffy.
- Pipes and sewage signs. Present: a pipe running in dry weather, staining below an outlet, grey water. Absent: a dry pipe, a natural seep.
- Warm-up pair: one tidy, pretty, damaged creek and one messy, healthy one, as similar in size and light as you can find.

## 17. First reply

Stay in plan mode. Reply with three things: PLAN.md with the sessions above sized for evenings and each ending in a proving command; the inputs you need from Rachel and Alex with the latest workable date for each; anything in this brief you would change, with your reason in a line. After Alex approves, write a CLAUDE.md of 60 lines or fewer that holds the hard rules as one line each plus the layout and commands, then start Session A.
