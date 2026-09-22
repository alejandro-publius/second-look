Track 3, AI-Supported Assessment. The track says citizen observations can be inconsistent and error-prone. We measure that, per person and per feature, with a two-minute photo test, and we save the result with every observation. AI takes the same test. It may only raise a question on features where it passed, and the volunteer always answers first.

# Second Look

Second Look spends two minutes teaching and testing a volunteer on the creek damage people usually miss, then saves their score with every observation they make, so a city knows how much to trust it.

**Take the two-minute test yourself. No camera needed.** https://second-look-79t.pages.dev

The landing page opens with two creek photos and one question: which creek is healthier? The photographs land with the picks on `main`; this branch shows none rather than a stand in.

## Results

Results arrive with the model run. Two things will stand here, and nothing is typed by hand:

- The test on strangers: mean share correct for the trained arm and the untrained arm, the difference, and its 95 percent bootstrap interval from the plan tagged before the first participant. If the interval covers zero the lesson showed no effect and this line will say so.
- Where a model may speak: for each of the three models and each of the four features, whether it passed, which is all four items right in at least two of three runs. Only a passed feature may ever produce a flag.

After the run, `evals/` write `results/`, `scripts/render_readme.py` fills this section from those files, and `scripts/verify_claims.py` checks every number against them in CI. Until then this section shows no table at all. The synthetic dry runs that proved the analysis code are in `results/` with the word SYNTHETIC on every file, and none of their numbers appears here.

## The problem

People judge a creek the way they judge a park. Tidy and green reads as healthy. OneAquaHealth's project lead said it in the first workshop: volunteers catch smell, foam and colour, and walk past concrete banks, a channel that was dug out, and pretty plants that do not belong. So the best-looking creek can get the best rating and deserve the worst.

Professional surveyors fixed this long ago. In the UK's River Habitat Survey, "only surveys from accredited surveyors will be entered on the RHS database", and accreditation means attending a course and passing a test (RHS manual 2003, pages 3 and 20; see `docs/notes/sources.md`). Volunteers have never had that. Their observations arrive with no mark of how far to trust them, and a city cannot tell a careful observer from a hopeful one.

## How the solution aligns with OneAquaHealth

OneAquaHealth says citizen data should stand beside lab data under the same profiles and value sets. A lab result is trusted because its quality checks travel with it. Second Look gives a volunteer's observation the same thing: their per-feature score, stored as a dated Practitioner qualification and linked through Provenance to every Observation they make. The four features are the ones the project lead named. The creek check mirrors the official Citizen Science App's items in its order and keeps its closing question about how the person feels at the stream. The health card ends in one action each for the person, the pet and the city. The city actions are OneAquaHealth's own restoration measures, from the [OneAquaHealth Policy Brief (2026), page 9](https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf): replant margins, fix sewers, reconnect the floodplain, remove barriers, take out the concrete. Every record validates against their implementation guide at commit b907cf0 with zero errors (`results/fhir_validation.json`). It improves monitoring of water ecosystems and their connection to human, animal and environmental health by making each observation carry its own trust mark.

## Innovation and practical value

Measure each volunteer, per feature, and store the measure with the data. Three things follow. The analyst sees "4 of 4 on built banks, tested Sep 23" beside an answer, never a blended grade or a probability. Follow-up questions are chosen by code from the answers, the person's scores and the weather, two at most: "It has not rained here for N days. Is anything coming out of that pipe?" We do not weight a group's vote by these scores: our own simulation says four photos per feature is too coarse for that, and a plain majority won. This is our answer to the citizen science challenge the track names, and we check it on strangers rather than assert it.

## Effective use of data, technology, AI, APIs and standards

- Standards: FHIR R4 4.0.1. The OneAquaHealth guide pinned at hl7-eu/oah b907cf0 (`fhir/ig.lock`), built from source with SUSHI 3.20.1, every emitted resource validated in CI with the HL7 validator. Their codes where they exist, ours only for the four features and "can't tell". UCUM units. Locations nest with partOf. Mapping: `docs/fhir_mapping.md`.
- APIs and data sources: their FHIR sandbox, read at one request per second and mirrored with conditional creates, `meta.tag` on everything and a ledger of ids; Open-Meteo for the 72 hour rainfall window behind the dry pipe rule; the Cal-IPC Inventory for the Bay Area plant list; public dry-weather screening guidance for the pipe rule; the River Habitat Survey's written cues for the channel and bank lessons.
- AI: vision models take the same 16-item test as the people, same wording, three runs. `core/gate.py` turns model output into Flag objects or drops it; a flag for a feature the model did not pass is dropped and logged; a flag can only make one follow-up question eligible. The record builder accepts human answers only. A fuzz test proves that for any model output the stored answers equal the human answers. The only model text a person ever sees is a short note labelled "the checker noticed".
- Data: no names, emails, addresses, free text or third-party scripts in the study flow; a random session id and a hashed random browser token; EXIF stripped from uploads, which are deleted after 30 days; a hash-chained audit log (`audit/log.jsonl`, an audit log, not a blockchain).

## A clear demonstration of what was built

- `/t`: consent, warm-up pair, server-side assignment in permuted blocks of four, the lesson for the trained arm, 16 items with Yes, No and Can't tell, the score per feature, the share card.
- `/demo`: judge mode with feedback after each answer, and the lessons only for what you missed. Stores nothing. `/demo?script=1` replays one fixed path for the video.
- `/check`: the guided creek check, one question per screen, with follow-ups chosen by `core/followups.py`.
- `/spot?id=`: the record, each answer beside the observer's score, "only people who passed this feature", what people reported upstream, View as FHIR with the validation badge and a curl line, the health card.
- `/city?creek=strawberry-creek`: the analyst's view. What people reported, what the creek needs in OneAquaHealth's own measures, which pipes are worth testing with a FHIR referral and an example of a result coming back, the reaches from the hills to the Bay with the downstream note. Every number opens the records behind it.
- `/two`: one lab Observation read from their sandbox and one volunteer Observation of ours in the same viewer.
- `/quick?spot=`: the 20 second return check. `/judges`: every door in the order that makes the point. `/poster`: the recruiting poster in Letter and A4. `/how-we-know`, `/about`, `/privacy`.
- A read only MCP server over our own records for any software agent, five tools, every answer with the resource ids behind it: `examples/mcp/README.md`.

## Try it

The test: https://second-look-79t.pages.dev on any phone or laptop, no camera needed. Judges start at https://second-look-79t.pages.dev/judges. Locally: `make dev`, then open http://localhost:3100.

Our data set as OneAquaHealth registers one, live on their sandbox: `curl -H "Accept: application/fhir+json" https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466`. The worked visit record it points at, validated against their guide: `fhir/golden/visit-strawberry-creek-1.json`. An agent: `uv run python -m apps.mcp.server --export data/export` after `make export-records`.

## How we know it works

- The analysis plan, `docs/analysis_plan.md`, is tagged `prereg-v1` before the first participant. The tag, the plan's SHA-256 and the audit log's hash at freeze are posted publicly on the day and written into this section by `scripts/render_readme.py` from `results/`, so they can be checked against the post.
- Two arms, randomized 1 to 1 in permuted blocks of four, server side. Trained: lesson then test. Untrained: test, then the lesson as a thank you. One confirmatory test: the difference in mean accuracy, percentile bootstrap with 10,000 resamples and a two-sided permutation test, seed 20260920. Exclusions were fixed in advance and each one's count is reported in `results/`.
- Participant flow: completed sessions per arm, randomized and started counts, the exclusion counts and the count by source are in `results/usability_<stamp>.json` after the run, and the completed counts stand in the results section.
- Below 20 completed sessions per arm the result is descriptive and the first screen says so.
- Deviations from the tagged plan: every one is in `docs/deviations.md`, with its date and reason.
- Gold labels are set blind from written definitions through `scripts/label_photos.py`, which never shows one labeller the other's file. With two labellers, Cohen's kappa per feature goes in `results/key_agreement.json` and every disagreement is settled before the key freezes; with one, the plan and this section say so. The key hash is in `results/key_hash.json` from the freeze.

## Architecture

```
collection      phone PWA (apps/web): /t test, /check creek check, /quick return check, photos downsized and EXIF stripped
    |
transformation  core/ pure functions: scoring, followups (2 at most, no model call), gate (model output -> Flag or dropped),
    |           labels ("4 of 4 on built banks"), fhir_emit (one visit -> Locations, Practitioner, QuestionnaireResponses,
    |           Observations, Provenance); rainfall from Open-Meteo, 72 hours, fail closed
    |
validation      content loader (every photo has a manifest row, lesson and test photos disjoint), HL7 validator + IG b907cf0
    |           in CI, verify_claims over this README, hash-chained audit log, tests for every hard rule
    |
aggregation     our store (SQLite locally, Cloudflare D1 in production) is the source of truth; evals/ write results/,
    |           including the usability analysis, the model sweep and the consensus analysis
    |
publication     /spot?id= and /api/fhir/Bundle/{visit} (read-only FHIR JSON), /city, the MCP server, the tagged mirror
                in the OneAquaHealth sandbox with a ledger, the Library entry there pointing at this repository, this README
```

## Feasibility: Berkeley as a follower city

OneAquaHealth calls a city that adopts the method a follower city and gives a five-step recipe (Workshop 4; Alex confirms the exact wording against the recording). Run on Berkeley:

1. Name the streams. Strawberry Creek, its reaches and spots become nested Locations under their Location profile. Two more East Bay creeks follow the same way.
2. Adopt the form. The creek check mirrors their Citizen Science App items, with stable ids that are FHIR linkIds, plus the two-minute test and its scores as a Questionnaire and QuestionnaireResponse.
3. Train and test the volunteers. Two minutes in the flow, per-feature scores that expire after 90 days, the lesson checked on strangers before launch.
4. Collect and validate. Every visit becomes Observations under their indicator profile with Provenance back to the observer's score, validated in CI before it is stored or mirrored.
5. Publish and repeat. Records to the sandbox with a tag and a ledger, a Library entry for the data set, return visits through the quick check, so one snapshot becomes a story.

Cost through Oct 15: nothing. Cloudflare Pages serves the site and a Worker with D1 and KV serves the API, on the free plan, with no card. Integration with existing systems is by their own profiles, so a city that already reads OneAquaHealth records reads ours.

## One Digital Health and FAIR

Story: a student walks to Strawberry Creek, takes a two-minute test on her phone, and from then on every observation she makes carries how well she sees each kind of damage. A city analyst reads her record beside a lab result under the same profile and knows how much weight to give each. The health card tells her one thing for herself, one for her dog and one her city could do.

Five dimensions, in words rather than numbers because no script produces them: citizen engagement, strong (the test, the check, the share card, repeat visits); education, strong (the lesson, checked on strangers); human and veterinary healthcare, partial (approved sentences for the person and the pet, no diagnosis, no site risk); industry 4.0, partial (FHIR records, a gated vision model, an audit log); environment, strong (four features of stream damage, the dry pipe rule, the regional plant list).

FAIR: findable through a Library entry in their sandbox and a public repository; accessible through a read-only FHIR endpoint and CC BY 4.0 copy; interoperable through their profiles, value sets and UCUM; reusable through MIT code, a pinned guide, Provenance on every record and a tagged analysis plan.

## Data and photo rights

Code is MIT (`LICENSE`). Our own photos and copy are CC BY 4.0. A photograph from somewhere else keeps its own licence: we take CC0, public domain, and CC BY or CC BY-SA at 2.0, 3.0 or 4.0, recorded at the exact version and never rounded up. Every image has a row in `photos/manifest.csv` with its source, author and licence, and every photograph a visitor can see is named with its author on `/credits`, which is what CC BY asks for. The web build refuses to run if a photograph that needs an author does not have one. No AI-generated images anywhere; no faces, house numbers or plates. The usability test is anonymous and the creek check is pseudonymous; `docs/DATA_HANDLING.md` says what is stored and what the hosts log on their own. Third-party dependencies and licences: `docs/THIRD_PARTY.md`.

## How this was built

Claude Code wrote most of the code and text in this repository, from briefs written by the two humans named in `docs/analysis_plan.md`. They supplied the idea, the photos, the labels, the wording and the judgment, and they own every approval flag. All work happened inside Sep 16 to 30, 2026, in small commits; nothing was copied from earlier projects. The sources behind the lesson drafts are listed with dates in `docs/notes/sources.md`.

## Known weaknesses

- 16 items is a small test. The per-feature model results in particular have wide intervals, and the pass rule is strict on purpose.
- The sample is whoever opens a link in one week in Berkeley. Below 20 completed sessions per arm the result is a description, not a claim.
- Photos are from East Bay creeks in one season and from open collections. The lesson may not transfer to other regions or seasons; the plant list is regional by design.
- People see the photo at phone size; models receive it resized to 1092 px on the long side.
- The dry pipe rule depends on Open-Meteo. When rainfall or location is unknown the question is skipped rather than guessed.
- The sandbox is shared and allows deletes; our store is the source of truth and the mirror can be rebuilt from the ledger.
- The form items are marked unverified until Alex checks them against screenshots of the official app. The app has no smell item; our quick check may ask about smell.
- Four photos per feature is a coarse measure. It is enough to show a person what to practise and to flag an answer worth a second look. It is too coarse to weight votes with, and our own simulation says so. The score sharpens each time a person retakes the test on new photos.
- The checker is off by default and speaks only on passed features. It may end up with nothing to say, and the results section will show that.
- English only. A Spanish locale ships only if a fluent person checks every string.
