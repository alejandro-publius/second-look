Track 3, AI-Supported Assessment. The track says citizen observations can be inconsistent and error-prone. We measure that, per person and per feature, with a two-minute photo test, and we save the result with every observation. AI takes the same test. It may only raise a question on features where it passed, and the volunteer always answers first.

# Second Look: Devpost draft

DRAFT, written 2026-09-20. Final numbers come from `results/` after data lock and are checked by `scripts/verify_claims.py`; every result slot below says SYNTHETIC PLACEHOLDER until then. The five headers are the organizers' (email of Sep 20), in their order.

Second Look spends two minutes teaching and testing a volunteer on the creek damage people usually miss, then saves their score with every observation they make, so a city knows how much to trust it.

Take the two-minute test yourself. No camera needed. DEMO_URL_PLACEHOLDER

## The problem

People judge a creek the way they judge a park: tidy and green reads as healthy. OneAquaHealth's project lead said in the first workshop that volunteers catch smell, foam and colour and walk past concrete banks, a channel that was dug out, and pretty plants that do not belong. So the best-looking creek can get the best rating and deserve the worst. Professional river surveyors solved this in the 1990s: in the UK's River Habitat Survey, only surveys from accredited surveyors, who attended a course and passed a test, are entered on the database. Volunteers have never had that, and their observations carry no mark of how much to trust them.

## How the solution aligns with OneAquaHealth

OneAquaHealth says citizen data should have the same standing as lab data, under the same FHIR profiles and value sets. A lab result is trusted because its quality checks travel with it. Second Look gives a volunteer's observation the same thing: the person's per-feature test score, stored as a Practitioner qualification and linked through Provenance to every Observation they make. The features are the ones the project lead named. The creek check mirrors the official Citizen Science App's items and keeps its closing question about how the person feels at the stream. The health card ends in one action each for the person, the pet and the city, and the city actions are the measures the project's Decision Support System returns: replant margins, fix sewers, reconnect the floodplain, remove barriers. Records validate against the OneAquaHealth implementation guide at commit b907cf0 with zero errors. Berkeley is a follower city, Strawberry Creek the worked example.

## Innovation and practical value

The idea is small and, as far as we know, new for citizen science: measure each volunteer, per feature, and store the measure with the data. Three things follow. The analyst sees "4 of 4 on built banks, tested Sep 23" beside an answer instead of a blended grade. A follow-up question is chosen by code from the answers, the person's scores, and the weather, two at most, for example "It has not rained here for N days. Is anything coming out of that pipe?" We do not weight a group's vote by these scores: our own simulation says four photos per feature is too coarse for that, and a plain majority won. The lesson is checked on strangers: half get the two minutes, half do not, everyone judges the same 16 photos, and the counting rules were published before anyone took it.

## Effective use of data, technology, AI, APIs and standards

- Standards: FHIR R4 4.0.1, the OneAquaHealth guide pinned at hl7-eu/oah b907cf0, built with SUSHI 3.20.1, every emitted resource validated in CI with the HL7 validator. Their codes where they exist (present, absent, morphology, invasive organisms, land use, foam, riparian vegetation), ours only where they do not. UCUM units. Nested Locations with partOf.
- APIs: the OneAquaHealth FHIR sandbox, read at one request per second and mirrored with conditional creates, a tag on every resource and a ledger of ids; Open-Meteo for the 72 hour rainfall window behind the dry pipe rule; a public read-only endpoint that serves any record as FHIR JSON with a curl line.
- AI: vision models take the same 16-item test as the people, three runs each. A model may flag a feature only if it passed that feature. Flags pass through a gate that turns model output into at most one follow-up question; the model never sets a label, never writes an answer, and the person has already answered before any flag is shown. A fuzz test proves stored answers equal human answers whatever the model returns.
- Data: no names, emails, addresses or free text; a random session id and a hashed random browser token; EXIF stripped from uploads; a hash-chained audit log over the plan tag, the frozen key, the wipe, the lock and every record write.

## A clear demonstration of what was built

- `/t`: consent, warm-up, random assignment, the two-minute lesson for one arm, the 16-item test, the score per feature, the share card.
- `/demo`: judge mode with feedback after each answer. No camera needed. `/demo?script=1` replays the same path for the video.
- `/check`: the guided creek check, one question per screen, with the dry pipe and rating check follow-ups chosen by code.
- `/spot/[id]`: the record, each answer beside the observer's score, View as FHIR with the validation badge, the health card.
- `/two`: one lab Observation from their sandbox and one volunteer Observation of ours in the same viewer.
- Results table (SYNTHETIC PLACEHOLDER): untrained people, trained people and each model on the same 16 photos, with the number of people. Primary difference with its 95 percent interval: SYNTHETIC PLACEHOLDER. Leaving out low scorers, exploratory: SYNTHETIC PLACEHOLDER.
- Video (3 to 5 minutes): VIDEO_URL_PLACEHOLDER. Repository: https://github.com/alejandro-publius/second-look (public on Sep 30).

## Devpost form fields, mapped to README sections

Alex pastes the exact fields of the Create Project form into `docs/notes/devpost_fields.md`. Until then, this is the mapping for the fields we can anticipate from the Devpost page (What to Submit: track alignment, project description, demo video, code repository, prototype or demo).

| Devpost field | Where it comes from |
|---|---|
| Project name | README title: Second Look |
| Tagline (short) | README line 3, the one sentence, cut to the character limit |
| Track alignment | README line 1, the track statement, word for word |
| Project description / About the project | README sections The problem through A clear demonstration of what was built, in order |
| Inspiration | README, The problem, first paragraph |
| What it does | README, A clear demonstration of what was built |
| How we built it | README, Architecture, then How this was built |
| Challenges we ran into | README, Known weaknesses |
| Accomplishments | README, Results table and How we know it works |
| What we learned | README, Results table (whatever it shows) and Known weaknesses |
| What's next | README, Feasibility: Berkeley as a follower city |
| Built with | FastAPI, Next.js, SQLite or Postgres, FHIR R4, SUSHI, HL7 validator, Open-Meteo, Claude models (see docs/THIRD_PARTY.md) |
| Try it out links | README, Try it: demo URL, repository URL, FHIR endpoint |
| Video demo link | `docs/video_script.md` recorded; the URL also goes in the README under Try it |
| Image gallery | The two warm-up photos and phone screenshots from `docs/screens/` |
| Team | Alex and Rachel; the page lists "Team required", so both are added |
| License | MIT for code, CC BY 4.0 for our photos and copy (README, Data and photo rights) |
