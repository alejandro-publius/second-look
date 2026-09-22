# Second Look: mammoth prompt 4 (the long run)

Paste this whole text into the Claude Code terminal. Everything below is addressed to Claude Code.

## 0. What this run is

Alex is away from the keyboard for hours and wants the most progress this project can make without him. Do not stop after Session A. Build the whole product end to end on placeholders, so that when the photos, labels and copy arrive, launching is a content swap and nothing else.

- Save this text as `docs/updates/UPDATE_04.md`. Where it disagrees with the master brief, Update 02 or Update 03, this file wins. In particular, the freeze on SHOULD items in Update 03 is lifted for this run. The order still holds: proofs first, MUST next, SHOULD after, COULD last.
- Do the work properly rather than cheaply. Write the tests, run them, fix what fails, review your own work. There is no ceiling on your own effort in this run. The only money caps are on paid model APIs (section 1).
- Never wait for a human. Where an input is missing, use a placeholder that is loudly marked, and make `make preflight` fail on it. A preflight that fails for human reasons only is the goal of this run.
- Use subagents in parallel for the workstreams in section 3. They own separate folders, so they do not collide. You integrate.
- After every phase: run its proving commands, commit, add five lines to `docs/BUILD_LOG.md` (what, proof, surprises, decisions, next), and re-read the hard rules in CLAUDE.md before going on.
- If your context gets tight, write `docs/HANDOFF_NEXT.md` (state, open threads, exact next command) and continue in a fresh subagent.

First, check where you are. Alex started you from his home folder. Run `pwd` and `git status`. All work happens inside one project folder, `~/second-look`, with its own git repo. If files from earlier prompts landed anywhere else, move them in. Never read, change or delete anything else in the home folder. Installing developer tools is fine.

## 1. Permissions and hard stops

You may, without asking:

- Install developer tools with Homebrew, npm, uv and pipx (Node 20, Java 17, SUSHI 3.20.1, the HL7 validator jar, Playwright browsers, Docker if present).
- Create a private GitHub repo with `gh` if it is logged in, and push. If it is not, commit locally and say so.
- Deploy to Vercel and Fly.io if those CLIs are already logged in. If they are not, make deployment one command and move on.
- Send read-only GET requests to the OneAquaHealth FHIR sandbox: one per second, 50 in this run at most, a user agent that names the project.
- Run the sandbox write test once: one Location tagged as ours, conditional create, read it back, delete that one record by its own id. Save the full output to `docs/notes/sandbox_write_test.txt` and mark K6 in `docs/KILL_TESTS.md`. Write nothing else there in this run.
- Fetch public web pages you need for sources (the River Habitat Survey manual and key, the Cal-IPC inventory, public stormwater screening guidance, Open-Meteo documentation and terms).

You must never, in this run:

- Create the `prereg-v1` tag, share a participant link, or store a real participant.
- Call `api.enora-oah.eu`.
- Delete by search or use `$expunge` on the sandbox.
- Spend on paid model APIs unless `ANTHROPIC_API_KEY` is already in `.env`. If it is: the P3 probe may spend 1 dollar, only if probe photos exist. Everything else runs against the fake client.
- Put any image in front of a person that is not a labelled gray placeholder or a real photo with a manifest row. Solid-colour frames for adversarial tests live in `evals/fixtures/` and are never shown to people.
- Make the repo public. Put a secret in git. Use an em dash or an en dash.
- Copy code from any earlier project of Alex's.

## 2. Phases

**Phase 0. Workspace, 15 minutes.** The folder check above. CLAUDE.md, PLAN.md, the brief and all updates in place. `.gitignore`, `.env.example`, the uv scaffold, the Makefile, CI. Proving command: `make check` green on the empty scaffold.

**Phase 1. Proofs, boxed.**
- P2 first, 90 minutes, exactly as Update 03 describes. Its outcome decides the shape of the FHIR workstream, so nothing in that workstream starts before it reports. Proving command: `make fhir-validate` prints the validator's verdict on our instances. On a pass, write `docs/fhir_mapping.md`. On a fail that is theirs to fix, write `docs/ig_gap_report.md`, take fallback F2 for the FHIR workstream (plain valid R4), and keep going with everything else.
- P1, 60 minutes: deploy the walking skeleton if the CLIs are logged in. If they are not, prove the same thing locally with `docker compose` (static page, API route, Postgres row written and read back) and leave `make deploy` ready.
- K6: the single sandbox write test.
- Write a mini report to `docs/BUILD_LOG.md` and carry on.

**Phase 2. Parallel build on placeholders.** Workstreams W1 to W7 in section 3.

**Phase 3. Integration.** `docker compose up` serves web, API and Postgres the way production will. End-to-end tests run against it. `make preflight` must fail, and its printed reasons must all be human inputs: photos, labels, question wording, approved copy, verified app items, the tag. If it fails for any other reason, fix that reason.

**Phase 4. Adversarial review.** Workstream W8, then fix what it finds, then run everything again.

**Phase 5. Extras.** Section 5, in order, until there is no useful work left.

**Phase 6. Report.** Section 7.

## 3. Workstreams and what done means for each

### W1. API and data (`apps/api/`)

- Tables from the master brief plus: `source_label`, `hidden_field_filled`, `post_lock`, `is_test`. Migrations that run on SQLite and Postgres.
- Allocator: permuted blocks of 4 for k arms from a stored seed, safe under concurrent requests. Tests: every complete block is balanced; two simultaneous sessions never share a slot; the sequence can be replayed from the seed.
- One UTC constant for data lock, `2026-09-28T01:00:00Z`. Sessions that start after it are stored as `post_lock` and never analysed. Tests one second either side.
- Responses are idempotent. The counts endpoint returns counts per arm and per source and nothing else. The export endpoint needs a token and contains no identifier. The demo route stores nothing.
- A short-lived in-memory rate limit per address, never written to disk or logs. The hidden form field. A test that captures the server log during a session and fails if a client address appears in it.
- A strict Content-Security-Policy that allows only our own origin, so the rule against third-party requests is enforced by the browser and not only by a test.
- `scripts/backup_db.sh`, `scripts/restore_db.sh` and a written restore drill that you run once against the compose database.

### W2. Analysis (`evals/`)

- `make_synthetic_sessions.py`: no effect, a real gain, a Yes bias with no gain, a wide spread of skill, equal skill.
- `usability_analysis.py`: the plan exactly. Exclusions applied in the plan's order with a count for each. Bootstrap and permutation with the fixed seed. Hedges g. Per-feature accuracy, hit rate and false-alarm rate. By source, by device, by prior experience. The warm-up item. JSON, a markdown table and one chart. It refuses real data before lock and refuses to run without the tag. `--synthetic` bypasses both and stamps every output SYNTHETIC in large letters.
- `power.py` writes `results/power.json`. A test checks that the planning note in the analysis plan agrees with it, or replace the note's numbers with a pointer to the file.
- `consensus.py`: amendment 6 of Update 02 exactly, with the weights 0, 0, 0.51 and 1.95 for 0, 1, 2 and 3 correct of the other three items. Tests: scored beats plain when skill varies; they tie within noise when skill is equal; a tie counts as wrong.
- Property tests with Hypothesis for the exclusions and for the vote arithmetic.
- `pick_examples.py` chooses README examples by the written rule.

### W3. The record in FHIR (`fhir/`, `core/fhir_emit.py`)

Shaped by P2's outcome.

- FSH for our CodeSystem, ValueSets, both Questionnaires and the example instances. The guide builds from the pinned commit with our examples inside it.
- The emitter turns one stored visit into resources: nested Locations, the pseudonymous Practitioner with its dated qualification, both QuestionnaireResponses, one Observation per answered item, one Provenance. Pure function. Golden-file tests.
- `make fhir-validate` runs the HL7 validator over everything the emitter produces in the tests. It caches packages, pins versions, and records whether terminology checks ran.
- Our own store of validated JSON. `scripts/repush_sandbox.py` with a `--dry-run` that prints what it would send, a ledger of ids, conditional creates only. Test it against a local HAPI container if Docker is present, otherwise against a mock server.
- `fhir/postman/second-look.postman_collection.json`: create, read and delete with creek records.
- A public read-only endpoint that serves a record as FHIR JSON, for the View as FHIR toggle and for fallback F2.
- `docs/ig_proposal.md`, one page, plain words, with the example.

### W4. Web (`apps/web/`)

- `/` static landing with the hook pair and one button. It paints without the API.
- `/t` the test flow from the master brief: consent with both checkboxes and the hidden field, warm-up, assignment, lesson for the trained arm, 16 items, end screen with the score per feature, the share card, the optional question. No feedback during the test. Per-photo answers hidden until the test closes.
- `/demo` judge mode with feedback after each answer and lessons only for the features missed. `/demo?script=1` is a fixed seeded path for the screen recording.
- `/check` the guided creek check, one question per screen, from `content/form.yaml`. Until Alex's screenshots arrive, fill the form from the app wording quoted in the master brief, every item marked unverified. The follow-up questions appear in place. Works offline: answers and downsized photos wait in a local queue and send later, with a clear "saved on this phone" state. If location is denied, the person drops a pin or picks a saved spot.
- `/spot/[id]` the creek's record: a timeline of visits, each answer beside the observer's score for that feature, the result of each check, the toggle "only people who passed this feature", View as FHIR with the validation badge and a curl line, and the health card.
- `/two` the two-observer screen: one lab Observation read from their sandbox and one volunteer Observation of ours in the same component. It caches in the database and says plainly when the sandbox is down.
- `/quick/[spot]` the 20 second return check.
- `/poster` the recruiting poster in Letter and A4, plus `make poster` to write PDFs. `?src=` links and QR codes that carry the source.
- `/about`, `/privacy`, `/how-we-know` in plain words.
- All strings in a locale file. System fonts. No third-party anything. Installable PWA with the lesson cached.
- Playwright on a phone viewport: both arms end to end; consent before assignment; no request leaves our origin; the keyboard-only path; the offline queue; the demo stores nothing. axe reports no serious violations. A Lighthouse budget for the landing page.

### W5. Core logic (`core/`)

- `gate.py`: the Flag model, the pass table check, the drop log. Hypothesis fuzz test: whatever a model returns, stored answers equal the human answers and every label equals the function of human answers alone.
- `followups.py`: a pure function over answers, site context, the person's scores and flags. The priority table lives in `content/followups.yaml`. Two questions at most. One test per rule and one for the cap.
- `rainfall.py`: an Open-Meteo client with a cache, a timeout and one retry. The dry rule is configurable (no more than 2.5 mm in the past 72 hours). On any failure it returns "unknown" and the dry pipe question is skipped. Record the terms and the attribution line in `docs/THIRD_PARTY.md`.
- `labels.py`: what the analyst sees. Raw "k of 4" and the test date. Expired after 90 days. No blended grade and no probability.
- `healthcard.py`: picks one action each for the person, the pet and the city from `content/approved_sentences.yaml`, and only sentences whose `approved` field is true. With none approved it shows nothing.

### W6. AI on the same test, and the checker (`evals/`, `core/`)

- `model_sweep.py` with a fake client and a real client behind a flag. Same question text, the resized photo, a forced answer plus a note of at most 160 characters, three runs, the Batch API for real runs. It writes the pass table and the cost log.
- The benchmark harness, Cohen's kappa per feature, and the ablation (rules only, context only, vision only, all three), all proven on fixtures.
- Adversarial fixtures: blank frames, an indoor scene drawn as flat shapes, a screenshot of text. The harness must end in no flag or Can't tell.
- The checker itself behind a feature flag: passed features only, one of the two follow-up slots, shown only after the person has answered, its note labelled "the checker noticed".

### W7. Tools and documents (`scripts/`, `docs/`, `audit/`)

- `ingest_photos.py`, `label_photos.py`, `merge_labels.py` and `freeze_key.py` as Update 02 and Update 03 describe. Try ingest on a folder of generated gray JPEGs with fake EXIF location data, and prove the location data is gone afterwards.
- `verify_claims.py`, `preflight.py`, `submit-check`, the audit log and `verify_audit.py`.
- `docs/DATA_HANDLING.md`, `THIRD_PARTY.md` (built from the lockfiles), `DECISIONS.md`, `KILL_TESTS.md`, `SUBMISSION_CHECKLIST.md`, `track_statement.md`, `release_form.md`, `video_script.md` (a draft on the beats in Update 02), `devpost.md` (a draft under the organizers' five headers), and the README in its final shape, with every result slot filled by a verified SYNTHETIC placeholder that verify_claims accepts only under a `--synthetic` flag.

### W8. Adversarial review

A separate subagent that did not write the code reads the repo against the master brief and the updates, and answers in `docs/reviews/REVIEW_01.md`:

- Can any model output reach a stored answer, a label or a user-facing sentence without passing the gate? Show the path or say none.
- Does anything store, log or send an address, a name, an email, a precise location or a fingerprint? Grep and show.
- Does any request leave our origin? Does any image lack a manifest row? Does any sentence about health reach a screen while unapproved?
- Can the analysis run on real data before lock or without the tag? Try it.
- Does every hard rule have a test or a gate that enforces it? List the ones that rest on good intentions alone.
- What would a stream ecologist object to in the draft lesson copy? What would a FHIR implementer object to in the mapping? What would a judge not understand in the first 30 seconds of the README?
- The ten ugliest pieces of code, and the ten places most likely to break on a phone at a creek.

Then fix what it found, most serious first, and run every proving command again.

## 4. Drafts that save the humans time

Everything here is marked DRAFT, carries `approved: false`, and cannot reach a screen until a human flips the flag. Preflight enforces that.

- `content/drafts/lessons/`: for each feature, a rule of thumb in 12 words or fewer, captions for two contrast pairs, and practice feedback that names the cue. Ground each in a source you actually fetched, and cite it: the River Habitat Survey's written signs of a reshaped channel (even sloped banks, a straightened course, the same width all along, slow flat water, no trees or trees all one age), the Cal-IPC inventory for Bay Area plants, public dry-weather screening guidance for the pipe rule. No health claims.
- `content/drafts/glossary.yaml`: every technical word in the form, in one plain sentence.
- `content/drafts/approved_sentences.yaml`: candidate actions for the person, the pet and the city, each with a source, none stating a risk for any site.
- `docs/rachel_pack.md`: one page. What we need from her and by when, the shot list, how to label blind, how to edit the YAML, what to check in the drafts.
- `docs/alex_today.md`: a checklist with the exact commands: `gh auth login`, `vercel login`, `fly auth login`, where to drop probe photos, how to log a kill test result, where the poster PDFs are.
- `docs/recruiting_messages.md`: a two-line chat message, a class announcement, a short email to a creek group, and the poster text. Plain words. No hype.

## 5. Extras, in this order, until there is no useful work left

1. An `es` locale drafted and marked unverified. It stays out of the build until Alex checks every string.
2. A small read-only MCP server over our own records: get a creek's record, list its visits, get an observer's score for a feature. With tests and a two-line README.
3. The downstream note: a finding on one reach adds a plain context line to the reaches below it, using the nested Locations.
4. The sampling referral: two different people report the same pipe running in dry weather, and the record gains a request for a sample. Code decides it. The wording stays "worth testing".
5. Load test the API at 50 sessions a minute on the compose stack and report the slowest endpoint.
6. A second pass on how it feels in the hand: tap targets, contrast in sunlight, one-thumb reach, the wait between photos. Attach phone-viewport screenshots of every screen to `docs/screens/`.
7. A third pass on the words. Read every string aloud in your head. If a sentence could sit in any project's README, cut it or make it specific.

## 6. Proving commands for the whole run

Run all of these at the end and put each one's key line in the report.

```
make check
make e2e
make fhir-validate
python evals/make_synthetic_sessions.py && python evals/usability_analysis.py --synthetic
python evals/consensus.py --synthetic
python evals/power.py
python scripts/verify_audit.py
make poster
docker compose up -d && make smoke
make preflight        # must FAIL, and only for human reasons. Paste the reasons.
make submit-check     # must FAIL only on: video link, public repo, real results
```

## 7. The report

The terminal cuts long output off when Alex copies it. So:

1. Write the full report to `docs/reports/<UTC timestamp>.md`: the report block from Update 02 with the gates line, then the repo tree to depth 2, then the list of printed preflight failures, then the adversarial review's top findings and what you did about each, then what is waiting on which human by when, then your own view in five plain lines of what is most likely to sink this project now.
2. Copy that file to the clipboard with `pbcopy` and say that you did.
3. Print only the report block in the terminal.
