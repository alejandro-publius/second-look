Track 3, AI-Supported Assessment. The track says citizen observations can be inconsistent and error-prone. We measure that with a two-minute photo test. Each volunteer gets a score for each of four kinds of creek damage, saved with every observation they make. The AI takes the same test. It may only ask a volunteer to look again, only where it passed, and only after the volunteer has answered. The AI's help must be measured, not assumed. A second test, planned before anyone took it, is designed to check whether that one question makes people more accurate; its benefit is not yet established. What the AI may and may not do is in its [model card](https://github.com/alejandro-publius/second-look/blob/main/docs/MODEL_CARD.md).

# Devpost: every field, ready to paste

UPDATE_14 section 8 item 1. Each field is one code block, so one tap copies it; where a count is given, it is characters, spaces included. The text is the paste kit from pull request #5 (its DEVPOST_PASTE.md, not copied), brought up to date: the video walks and the creek footage are added, and every number carries a claim marker checked against `results/` by `uv run python scripts/verify_claims.py --file docs/devpost.md`, except the names and fixed facts that `scripts/submit_check.py` lists with a reason each (a version, a model's name, the 72 hour rain window). The track statement is this file's first line, as it is the README's. This file is the one to paste from.

The video link is a slot on purpose. The paid model run happened on Sep 23 and 24; its numbers live in the README's AI table, checked against `results/`, and this text states the pass table only in words.

## Project name

11 characters

```text
Second Look
```

## Tagline (under 200 characters)

141 characters

```text
A two-minute photo test that scores volunteer creek observers, then saves each score with every observation they make, as OneAquaHealth FHIR.
```

## Track statement (line one of the description)

```text
Track 3, AI-Supported Assessment. The track says citizen observations can be inconsistent and error-prone. We measure that with a two-minute photo test. Each volunteer gets a score for each of four kinds of creek damage, saved with every observation they make. The AI takes the same test. It may only ask a volunteer to look again, only where it passed, and only after the volunteer has answered. The AI's help must be measured, not assumed. A second test, planned before anyone took it, is designed to check whether that one question makes people more accurate; its benefit is not yet established. What the AI may and may not do is in its [model card](https://github.com/alejandro-publius/second-look/blob/main/docs/MODEL_CARD.md).
```

## The problem

793 characters

```text
People judge a creek the way they judge a park: tidy and green reads as healthy. OneAquaHealth's project lead said it in the first workshop. Volunteers catch smell, foam and colour, and walk past concrete banks, a channel that was dug out, and pretty plants that do not belong. So the best-looking creek can get the best rating and deserve the worst.

Professional surveyors fixed this long ago. In the UK's River Habitat Survey, only surveys from accredited surveyors are entered on the database, and accreditation means a course and a test. Some volunteer programs certify people for a method, such as water chemistry. None we know of measures how well each volunteer sees each feature, or keeps that score with every observation, so a city cannot tell a careful observer from a hopeful one.
```

## How the solution aligns with OneAquaHealth

939 characters
<!-- claim: results/fhir_validation.json#/errors = 0 -->

```text
OneAquaHealth says citizen data should stand beside lab data under the same profiles and value sets. A lab result is trusted because its quality checks travel with it. Second Look gives a volunteer's observation the same thing: their score per feature, stored in the record of their test sitting beside a dated Practitioner qualification, and linked through Provenance to every Observation they make.

The four features are the ones the project lead named. The creek check asks the official Citizen Science App's questions word for word, in its order and in six of its languages. The health card ends in one action each for the person, the pet and the city, and the city actions are OneAquaHealth's own restoration measures from the OneAquaHealth Policy Brief (2026), page 9. Sample records from both emitters validate against their implementation guide at commit b907cf0 with zero errors, and golden vectors hold the live emitter to them.
```

## Innovation and practical value

```text
Measure each volunteer, per feature, and store the measure with the data. The analyst sees "4 of 4 on built banks, tested Sep 23" beside an answer, never a blended grade or a probability. A city picks its own threshold.

Follow-up questions are chosen by code from the answers, the person's scores and the weather, two at most. For example: "It has not rained here for N days. Is anything coming out of that pipe?" A pipe running in dry weather is worth a lab test, and the record already has the shape for sending that request and for the result coming back.

The hosted prototype uses Cloudflare's free tiers, subject to their limits. Model evaluation, optional recruitment and ongoing maintenance are separate costs. The adoption guide follows OneAquaHealth's five-step recipe; a real city integration still needs local configuration and validation.
```

## Effective use of data, technology, AI, APIs and standards

1607 characters

<!-- claim: results/fhir_validation.json#/errors = 0 -->
<!-- claim: results/footage_pool.json#/frames_kept = 46 -->
<!-- claim: results/footage_pool.json#/videos_kept = 5 -->
<!-- claim: results/footage_pool.json#/countries_kept = 3 -->
<!-- claim: results/footage_latest.json#/gate/dropped = 29 -->
<!-- claim: results/footage_latest.json#/gate/candidates = 64 -->
<!-- claim: results/benchmark_20260924T054939Z.json#/pool/n_photos = 16 -->

```text
Standards: FHIR R4 4.0.1. The OneAquaHealth guide pinned at hl7-eu/oah b907cf0, built with SUSHI 3.20.1, and sample records from both emitters validated in CI with the HL7 validator, with 0 errors in the latest run. Their codes where they exist, ours only for the four features and "can't tell". UCUM units. Nested Locations.

APIs: their FHIR sandbox, read at one request a second and mirrored with conditional creates, a tag on every resource and a ledger of ids, plus a Library entry there for our data set. Open-Meteo for 72 hours of rain behind the dry pipe rule. A read-only MCP server over our own records for software agents.

AI: vision models take the same 16-photo test as people, same words, three runs, and the same pipeline ran on 46 frames from 5 openly licensed creek videos in 3 countries, each frame screened by Apple Vision for people and text and then checked by eye; there the gate dropped 29 of 64 candidate flags, each for a feature that model had not passed. Every model passed built banks and none passed invasive plants; Claude Opus 5.5 and Fable 5.1 also passed pipes, and Haiku 4.5, Sonnet 5 and Opus 5.5 the dug-out channel. A model may raise a flag only on a feature it passed. core/gate.py turns model output into a flag or drops it, and a flag can only make one follow-up question eligible. The person always answers first, and a fuzz test proves the stored answers equal the human answers whatever the model returns.

Data: no names, emails or free text in the test; a random session id; EXIF stripped from uploads, which are deleted after 30 days; a hash-chained audit log.
```

## A clear demonstration of what was built

1729 characters
<!-- claim: results/footage_pool.json#/walks = 3 -->
<!-- claim: results/footage_pool.json#/walk_country_count = 3 -->
<!-- claim: results/benchmark_20260924T054939Z.json#/pool/n_photos = 16 -->

```text
Take the test: https://second-look-79t.pages.dev (no camera needed).
Judges start here: https://second-look-79t.pages.dev/judges

/t: consent, warm-up, then the lesson and 16 photos, in an order the server picks at random (half the people see the photos first and get the lesson after their score), and a score per feature.
/demo: judge mode with feedback after each answer. Shut while the study's second wave runs, because it shows the answers to the study's photos; open from that wave's lock.
/t2/demo: the AI's one question. Eight photos; when the checker disagrees with your answer it asks you to look again, and you decide. Nothing is stored. Open from the same lock.
/check: the guided creek check in the official app's own words and six languages, one question per screen, with follow-ups chosen by code.
/walk/v02, then "See this creek as a city would": the record your answers make, each answer with its FHIR, and what the creek needs in OneAquaHealth's own measures. The clips show natural creeks, so a measure appears when the walk reports damage, for example Artificial for the bank. /city?creek=strawberry-creek stays empty until the first real check.
/two: a volunteer Observation of ours beside a lab result from their sandbox, in the same viewer, with the time the lab result was fetched.
/how-we-know: which features each vision model passed on the 16-photo test, and what the gate kept and dropped on real creek footage, with the frames.
/walk: check a creek from your desk. 3 short clips of creeks in 3 countries, the same check while you watch, and a demo record with its own link, never counted.

Video: [VIDEO LINK] (released under CC BY-SA 4.0; creek footage from Wikimedia Commons, credited in the video)
```

## Users and impact on ecosystem and human health

784 characters

```text
Users: volunteers who check creeks, and the city and project staff who read their records.

Ecosystem: the four features people miss are built banks, a dug-out channel, invasive plants, and pipes and drain outlets; the answers on built banks and pipes tell a city what a creek needs. The official app has no question for a dug-out channel, so the check asks none, and plants have no city measure of their own. Scoring observers per feature means a city can act on the observations it can trust, and send a lab test where two trained people both saw a pipe running in dry weather.

Human and animal health: the health card gives one action for the person, one for the pet and one for the city, each from an approved sentence with its source. It never states a risk for a specific site.
```

## Built with

139 characters

```text
python, fastapi, typescript, next.js, cloudflare-workers, cloudflare-d1, cloudflare-pages, fhir, hl7, sushi, open-meteo, playwright, claude
```

## Live link

33 characters

```text
https://second-look-79t.pages.dev
```

## Judges link

40 characters

```text
https://second-look-79t.pages.dev/judges
```

## Repository

48 characters

```text
https://github.com/alejandro-publius/second-look
```

## Technical report

Attach `docs/REPORT.pdf` to the submission where Devpost takes a file, and link it from the
text as https://github.com/alejandro-publius/second-look/blob/main/docs/REPORT.pdf once the
repository is public. It is built by `make report-pdf` from the README and `results/`, and a test
in `make check` fails when it is older than its sources. This section is not a paste field.

## Video link

50 characters

```text
[VIDEO LINK: paste the upload URL here on the day]
```

The video is released under CC BY-SA 4.0, because several of the creek clips in it are CC BY-SA. The creek footage and photos are openly licensed files from Wikimedia Commons, not our own; each one is credited on screen, in `docs/video/CREDITS.md` and on the app's `/credits` page. Put the same licence line in the video's description where it is uploaded. This paragraph has no link on purpose: `make submit-check` looks for a line with the word video and a link, and only the real upload link may pass it.

## Gallery images, in this order

Upload these five, 1500 by 1000 each, from `docs/submission/gallery/` (made by `uv run python scripts/make_devpost_gallery.py` from the screenshots `make screens` takes). Paste each caption under its image. Images 1 and 5 are screenshots of the live site; 2 to 4 are of this commit's production build with a fake API, so taking them added no sitting or visit to the study.

1. `1-which-creek.png`: The first screen: two real creeks and one question. The tidy park hides a concrete channel.
2. `2-lesson-card.png`: A lesson card: numbered marks on a real photo show what to look for before the test.
3. `3-score.png`: The score screen: one gauge for each of the four features, so a volunteer sees what to practise.
4. `4-record-and-fhir.png`: A creek record shows each answer beside the observer's score, and View as FHIR shows the same record in OneAquaHealth's profiles.
5. `5-city.png`: The city view: what the creek needs, in OneAquaHealth's own restoration measures, each with its source.

## Team

Alex Velazquez and Rachel Selbrede (https://github.com/rachelselbrede). Confirm that Rachel has accepted the GitHub invitation and joined the Devpost draft; these are separate steps (docs/ALEX_TODO.md).
