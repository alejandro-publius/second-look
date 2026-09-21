# Second Look: mammoth prompt 10 (the full loop, and the repo shape that won before)

Paste this whole text into Claude Code, in the window that is open or in a fresh one. It needs nothing from Alex. Everything below is addressed to Claude Code.

**Three answers to your last report.** The `depth` branch does not exist yet: this prompt creates it. Built banks: keep our question, because the test needs a question and the app's text is a statement. Backups: take the schedule off until the two secrets exist, and leave the launch gate red on that line.

**Set up a separate working copy first,** so this work can never collide with the launch build that Alex will run in `~/second-look`:

```
cd ~/second-look && git fetch && (git worktree list | grep -q second-look-depth || git worktree add ../second-look-depth -b depth)
cd ~/second-look-depth && uv sync && (cd apps/web && npm ci)
```

Do all of this prompt's work in `~/second-look-depth`, on the `depth` branch. Do not edit, stage or commit anything in `~/second-look` during this prompt. Read `CLAUDE.md`, `PLAN.md` and `docs/HANDOFF_NEXT.md` from the worktree first, and nothing else yet. Save this text there as `docs/updates/UPDATE_10.md`. It lifts the freeze for the items it names and for nothing else. Every hard rule stands: the gate, approved sentences only, no risk stated for a specific site, no calls to `api.enora-oah.eu`, sandbox etiquette, no paid model call without a key in `.env`, the privacy rules, no em or en dashes, no emoji.

Work tier by tier. After each tier: `make check` green, commit, refresh `docs/HANDOFF_NEXT.md`, add the tier to the report file. Then go straight on to the next tier. If billing stops you, the handoff is already current. At the end, or when stopped, copy the full report to the clipboard with `pbcopy` and print the report block.

## A. Answers to the three questions from your Update 09 report

1. **The pages.dev link is fine. No domain.** A poster and a group chat do not need one, and a domain costs money and a day. What matters is that the link never changes once it is printed: settle the Pages project name now and never rename it. Also put the API behind the same origin. Serve it under `/api/*` on the pages.dev site, through a Pages Function or a service binding to the Worker, so the browser talks to one origin only. That removes CORS, lets the policy say `connect-src 'self'`, and sidesteps networks that block workers.dev.
2. **The backup workflow waits.** Switch it to manual runs only, so it never shows a red failure. When Alex has added the two secrets, turn the schedule back on, run it once, and do the restore drill. Preflight requires one good backup and one restore drill before launch.
3. **No second deploy. The Worker becomes the one production API.** Judges arrive on Oct 1, so nothing is late. Python stays the reference implementation and the toolchain: analysis, evals, FHIR validation, scripts. Anything a judge touches live has to run on the Worker. Port it the safe way: the Python code writes golden vectors (inputs and expected outputs as JSON) for the follow-up selector, the labels, the health card picker, the duplicate guard and the FHIR emitter, and the TypeScript versions must reproduce them exactly in CI. The HL7 validator then checks the TypeScript emitter's output as well, because it does not care which language wrote the JSON. Port only what `/judges` needs, in this order: the creek check with its follow-ups and rainfall lookup, the record with View as FHIR, `/city`, the two observer screen.

## B. Two rules for this whole prompt

- **The launch build is protected.** Production deploys come from `main` only. All of this prompt's work lives on the `depth` branch in the `~/second-look-depth` worktree, which Cloudflare Pages serves at its own preview link (`wrangler pages deploy` with the branch set to `depth`). The test flow (landing, consent, lesson, test item, end screen, the study endpoints) is frozen from now until data lock, except for a fix that blocks launch. Merge `depth` into `main` only after `make check` and the phone end-to-end tests pass against the preview link, and never between the `prereg-v1` tag and data lock unless the test flow's files are untouched by the merge. Prove that with a diff.
- **The MCP server runs locally.** That is how agents use one. It reads the public read-only FHIR endpoint or a local export, and needs no hosting.

## 0. Why this prompt exists

The product has been described as one thing: a two-minute test. That undersells what is built and leaves real depth on the table. Alex's Blackbox repo won a grand prize out of 600 projects with a different shape: one loop that does real work end to end, touches every surface of the sponsor's platform, writes back into it, and proves each step with a table a judge can check in 45 seconds. Second Look gets the same shape.

The loop, in five verbs, which line up with OneAquaHealth's own five pipeline stages (collection, transformation, validation, aggregation, publication):

**TRAIN, CHECK, VERIFY, RECORD, ACT.**

- TRAIN: a volunteer passes a two-minute photo test. AI takes the same test.
- CHECK: a guided creek check in the official app's own questions, a 20 second return check, offline at the creek.
- VERIFY: code picks at most two follow-up questions from the answers, the weather and the person's own score. AI may only ask, and only where it passed. Duplicate pins are caught.
- RECORD: every visit becomes FHIR that validates against their guide with terminology on, carries the observer's score, lands in our store, and mirrors to their sandbox.
- ACT: the creek's record turns into what the creek needs and which pipes are worth testing, for the person, the pet and the city, and into an answer any software agent can fetch with its evidence attached.

The line for the top of the README: **People look. Code checks. AI may only ask.**

Three kinds of people use it: the volunteer, the city analyst, and the developer or agent that reads the data.

First write `docs/DEPTH_MAP.md`: one table with a row per feature. Columns: verb, feature, status (built, parked, missing), main file, test, rubric line it serves, which kind of judge cares (ecologist, data tools, digital health, standards, agents and integration, outreach). Build it from the repo, not from memory. Everything below fills the gaps that table shows.

## 1. Tier 1: turn records into action

This is the biggest rubric line, and the hackathon co-lead's own gloss on innovation is turning data into actionable health insights.

1. **`/city`.** For each creek: visits, open findings by feature, and two lists decided by code.
   - "What this creek needs": findings mapped to the measures the project lead's decision tool returns. A built bank points at replanting margins. A pipe running in dry weather points at fixing sewers. A dug-out channel points at reconnecting the floodplain. A barrier points at removing barriers. Sentences come from the approved list only.
   - "Pipes worth testing": a pipe reported running in dry weather by two different people who both passed the pipe feature.
   - Every number on the page opens the FHIR resources behind it. No number without its ids.
2. **The referral and the way back.** A pipe on the "worth testing" list creates a FHIR ServiceRequest whose subject is the pipe's Location and whose reasons are the two Observations. Then show how a lab result would return to the same record: a Specimen and its Observations, under their Specimen profile if the guide has one, otherwise plain R4. Their roadmap names microbial metagenomics, so make the example a small panel result. It is an example: watermarked "example" on screen, tagged as an example in FHIR, never counted in any number, and listed under real versus synthetic.
3. **Duplicate and test pin guard.** A new spot within 30 metres of an existing one offers "add a visit to this spot" first. Names that look like tests are flagged for review and kept out of `/city`. Pure functions with tests.
4. **The downstream note.** Our store knows which reach flows into which. A finding on one reach adds one plain line to the reaches below it: "Upstream of here, two people reported a pipe running on Sep 22."

## 2. Tier 2: for the standards people and the agents people

1. **Write back.** Mirror the sample creek's record to their sandbox: tagged, conditional creates, the ledger, the repush script. Register a Library entry there that describes our data set and points at our repository, which is their own FAIR pattern. Save the evidence and a screenshot path at once, because anyone can delete records there.
2. **An MCP server, read only, over our own records, run locally over stdio.** Tools: `list_creeks`, `get_creek_record`, `list_findings` (by feature, minimum number of observers, passed only), `get_observer_score`, `explain_number` (returns the resource ids behind a figure). Every answer carries resource ids, so an agent cannot state a number it cannot trace. Contract tests, and one short transcript in `examples/mcp/`.
3. **`make new-city`.** Given a name and coordinates it scaffolds a region pack stub, the nested Locations in FSH, a poster, and a checklist that follows their five replication steps. Run it once for Heraklion, which they named as a follower city, as a dry example in English with no claims. Record how long Berkeley and Heraklion each took.
4. **The proposal.** Finish `docs/ig_proposal.md` and keep its FSH example building inside their guide at the pinned commit.

## 3. Tier 3: the README and docs in the shape that won

Model it on `alejandro-publius/blackbox-datahub`. Fetch that README and read it once for structure only. Copy no text and no code. Sections, in this order:

1. Title, the blockquote (one bold line, the three short sentences, one paragraph, the five verbs), then badges: CI, licence, tests passing, FHIR validation with 0 errors and terminology on, guide commit.
2. Screenshots from Playwright. Real photos when they exist, otherwise left out. Never gray blocks in the README.
3. **See it work.** One table from one real visit at Strawberry Creek once it exists: what the person reported, which follow-ups code chose and why, what validated, what was written to the sandbox, what `/city` then said the creek needs. Until it exists, the slots are marked and verify_claims keeps them honest.
4. **Why trust a volunteer, and the AI?** A table of failure mode, structural defence and proof (a test or a file). Rows at least: a volunteer walks past a built bank; someone taps at random; a pretty creek gets the best rating; a pipe report means nothing without the weather; the model invents a feature; the model was never good at that feature; duplicate and test pins fill the map; a record that a city's systems cannot read; someone edits history; we fool ourselves with the statistics; judge mode leaks the answer key; a refresh loses a session.
5. **What the AI cannot do.** A table of constraint and what enforces it, each with a file and a test.
6. **Architecture.** A Mermaid flowchart of the whole system grouped by the five verbs, then a short list under "Why this architecture matters". A second Mermaid diagram of the FHIR resources and how they point at each other. A third, a sequence diagram of the AI gate: photo, model, flag, gate, at most one question, the person answers, the record, with the model never writing. Add `make diagrams`, which checks every Mermaid block parses, and put it in CI.
7. **How OneAquaHealth is used.** A table of surface, what we use it for, and where in the repo: the official app's question wording; their Location and Observation profiles; their value sets and UCUM; a Questionnaire attached through their form extension; nested Locations; the HL7 validator with their guide and terminology on; the sandbox write and the Library entry; the decision tool's measures; the five One Digital Health dimensions; FAIR; the follower city recipe; the roadmap item on metagenomics.
8. **Contributed back.** The proposal, the two gaps the validator run exposed in their guide, and anything else Alex confirms.
9. **Evals.** The pre-registered test on strangers, AI on the same test, the low scorer filter, all graded by code.
10. **What is real and what is synthetic**, in full.
11. **For judges.** A 45 second path of links, then `make judge-check`: no key and no network, it runs the tests, validates the committed FHIR examples, builds the web app, verifies the audit log and scans for secrets, and prints a five line summary. Then a table of where to find the proof: acceptance, a sample record, eval results, architecture, the scorecard, the demo script.
12. `docs/JUDGE_SCORECARD.md`: our own score against each rubric line with the weaknesses written in. `docs/ACCEPTANCE.md`: every gate with the command that proves it. `docs/ARCHITECTURE.md`: the deep version.
13. Repo map. Licence.

## 4. Tier 4: how it feels

1. Stage 2 of the design pass from `docs/updates/UPDATE_06.md` section 3, now including `/city` and `/judges`.
2. The Spanish draft, marked unverified until Alex signs it.
3. `make readability`: every UI string at or below a set reading grade, with a short exceptions list, inside `make check`.

## 5. Report

For each tier: what shipped, the proving command and its key line, what was cut and why. Then the depth map's counts of built, parked and missing, the `make judge-check` output, and the three things you think a judge would still find thin.
