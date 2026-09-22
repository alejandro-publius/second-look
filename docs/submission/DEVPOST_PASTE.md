# Devpost: every field, ready to paste

This supersedes the paste text in `docs/devpost.md` (the draft of Sep 20, which still has placeholders); keep that file for its field mapping table. Each field is one code block, so one tap copies it. The counts are characters, spaces included. Headers are the organizers' five, in their order.

Check before pasting: every number here is marked with a claim comment and checked against `results/` by the command at the bottom. The video link and any model result are left as slots on purpose.

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

350 characters

```text
Track 3, AI-Supported Assessment. The track says citizen observations can be inconsistent and error-prone. We measure that, per person and per feature, with a two-minute photo test, and we save the result with every observation. AI takes the same test. It may only raise a question on features where it passed, and the volunteer always answers first.
```

## The problem

700 characters

```text
People judge a creek the way they judge a park: tidy and green reads as healthy. OneAquaHealth's project lead said it in the first workshop. Volunteers catch smell, foam and colour, and walk past concrete banks, a channel that was dug out, and pretty plants that do not belong. So the best-looking creek can get the best rating and deserve the worst.

Professional surveyors fixed this long ago. In the UK's River Habitat Survey, only surveys from accredited surveyors are entered on the database, and accreditation means a course and a test. Volunteers have never had that. Their observations arrive with no mark of how far to trust them, so a city cannot tell a careful observer from a hopeful one.
```

## How the solution aligns with OneAquaHealth

784 characters

<!-- claim: results/fhir_validation.json#errors = 0 -->

```text
OneAquaHealth says citizen data should stand beside lab data under the same profiles and value sets. A lab result is trusted because its quality checks travel with it. Second Look gives a volunteer's observation the same thing: their score per feature, stored as a dated Practitioner qualification and linked through Provenance to every Observation they make.

The four features are the ones the project lead named. The creek check follows the official Citizen Science App's items in its order. The health card ends in one action each for the person, the pet and the city, and the city actions are OneAquaHealth's own restoration measures from the OneAquaHealth Policy Brief (2026), page 9. Every record validates against their implementation guide at commit b907cf0 with zero errors.
```

## Innovation and practical value

681 characters

```text
Measure each volunteer, per feature, and store the measure with the data. The analyst sees "4 of 4 on built banks, tested Sep 23" beside an answer, never a blended grade or a probability. A city picks its own threshold.

Follow-up questions are chosen by code from the answers, the person's scores and the weather, two at most. For example: "It has not rained here for N days. Is anything coming out of that pipe?" A pipe running in dry weather is worth a lab test, and the record already has the shape for sending that request and for the result coming back.

It costs nothing to run: Cloudflare's free plan, no card. A follower city adopts it with OneAquaHealth's own five steps.
```

## Effective use of data, technology, AI, APIs and standards

1158 characters

<!-- claim: results/fhir_validation.json#errors = 0 -->

```text
Standards: FHIR R4 4.0.1. The OneAquaHealth guide pinned at hl7-eu/oah b907cf0, built with SUSHI 3.20.1, and every emitted resource validated in CI with the HL7 validator, with 0 errors in the latest run. Their codes where they exist, ours only for the four features and "can't tell". UCUM units. Nested Locations.

APIs: their FHIR sandbox, read at one request a second and mirrored with conditional creates, a tag on every resource and a ledger of ids, plus a Library entry there for our data set. Open-Meteo for 72 hours of rain behind the dry pipe rule. A read-only MCP server over our own records for software agents.

AI: vision models take the same 16-photo test as people, same words, three runs. A model may raise a flag only on a feature it passed. core/gate.py turns model output into a flag or drops it, and a flag can only make one follow-up question eligible. The person always answers first, and a fuzz test proves the stored answers equal the human answers whatever the model returns.

Data: no names, emails or free text in the test; a random session id; EXIF stripped from uploads, which are deleted after 30 days; a hash-chained audit log.
```

## A clear demonstration of what was built

669 characters

```text
Take the test: https://second-look-79t.pages.dev (no camera needed).
Judges start here: https://second-look-79t.pages.dev/judges

/t: consent, warm-up, lesson, 16 photos, a score per feature.
/demo: judge mode with feedback after each answer.
/check: the guided creek check, one question per screen, with follow-ups chosen by code.
/spot: the record, each answer beside the observer's score, View as FHIR with the validation badge, the health card.
/city: the analyst's view of Strawberry Creek, with what the creek needs in OneAquaHealth's own measures.
/two: a lab Observation from their sandbox and a volunteer Observation of ours in one viewer.

Video: [VIDEO LINK]
```

## Users and impact on ecosystem and human health

632 characters

```text
Users: volunteers who check creeks, and the city and project staff who read their records.

Ecosystem: the four features people miss (built banks, a dug-out channel, invasive plants, pipes and drain outlets) are the ones that tell a city what a creek needs. Scoring observers per feature means a city can act on the observations it can trust, and send a lab test where two trained people both saw a pipe running in dry weather.

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

## Video link

50 characters

```text
[VIDEO LINK: paste the upload URL here on the day]
```

## Check

`scripts/verify_claims.py` reads README.md only, so point it at this file for one run:

```bash
uv run python -c "import sys, scripts.verify_claims as v; v.README = v.ROOT / 'docs/submission/DEVPOST_PASTE.md'; sys.argv = ['v']; sys.exit(v.main())"
```
