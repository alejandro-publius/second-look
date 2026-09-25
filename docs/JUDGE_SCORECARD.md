# Judge scorecard

The five criteria the organizers score, 1 to 10 each, with where to look for each one and what is still thin, as of 2026-09-24. Written for judges who have a few minutes. Every claim points at a file or a command, and nothing here is a result number: those live in `results/` and the README. Under each heading is our own mark, in words rather than a number, because it is our judgment and not a measurement.

The technical report, [`docs/REPORT.pdf`](REPORT.pdf), says the same at more length.

## Impact and alignment with the OneAquaHealth mission (30%)

Our mark: strong. The per-feature score travels with every observation in their own profiles, and the city view speaks only in their own measures.


| What to look at | Where |
|---|---|
| The problem, in the project lead's own words: volunteers miss built banks, dug-out channels and invasive plants | README, Why trust a volunteer, and the AI?; `docs/devpost.md`, The problem |
| The score travels with every observation: the test sitting's QuestionnaireResponse holds it, a dated Practitioner qualification names the test, and Provenance links both to every Observation | `fhir/golden/visit-strawberry-creek-1.json`; `/two`, an answer beside "4 of 4 on this feature" |
| City actions are OneAquaHealth's own restoration measures, from their Policy Brief (2026), page 9 | `/walk/v02`, then "See this creek as a city would"; the live creek page stays empty until the first real check |
| One action each for the person, the pet and the city, from approved sentences with sources | `content/approved_sentences.yaml`; the health card on the sample record, `docs/screens/spot-health.webp` (local build) |

Thin: no person has taken the test yet, so there is no measured effect of the lesson on people. A paid research panel may add sessions before the data lock on Sep 28, if Alex launches it; they would count in the one pre-registered analysis, reported whatever it shows. Said in README, Known weaknesses.

## Innovation and creativity (20%)

Our mark: strong. Testing observers is old in professional surveys; doing it in about four minutes, inside the flow, and storing it with the data is what is new.


| What to look at | Where |
|---|---|
| A volunteer is tested per feature and the score is stored with the data, like a lab's quality checks | README, Why trust a volunteer, and the AI?; `docs/devpost.md`, Innovation and practical value |
| The AI takes the same test and may only speak on a feature it passed | `core/gate.py`; `results/model_pass_table.json` |
| Follow-ups chosen by code from answers, scores and the weather, two at most | `core/followups.py`; `/check` |
| The whole loop from a desk: a clip of a creek somewhere else, the same check, a record made on the phone and never stored | `/walk`; `core/walks.py`; `content/walks.yaml` |

Thin: the AI is held to the same test, and no model passed plants that do not belong, so the checker never speaks on plants; four photos per feature is a small test (README, Numbers at a glance; `docs/MODEL_CARD.md`).

## Technical implementation (20%)

Our mark: strong. The paid model run is done and every AI number is graded again from its raw replies by `make reproduce`.


| What to look at | Where |
|---|---|
| FHIR R4 against their guide at b907cf0, validated in CI, zero errors in the latest run | `results/fhir_validation.json`; `make fhir-validate` |
| Their sandbox mirrored with conditional creates, a tag on everything, a ledger of ids | `fhir/sandbox_ledger.jsonl`; `docs/notes/sandbox_library.md`, the read-back |
| A read-only MCP server over our own records | `apps/mcp/server.py`; `examples/mcp/transcript.md` |
| One command, no key, no network | `make judge-check` |
| Frames from open creek footage, screened by Vision and by eye, every drop with its reason | `videos/frames.json`; `videos/review.json`; `evals/footage.py` |
| Python and the TypeScript Worker proved equal by golden vectors, walks included | `evals/golden_vectors.py`; `worker/test/golden.test.ts` |

Thin: the citizen observer is modelled as a Practitioner because R4 has no better fit; the question is open with the guide's authors (`docs/ig_proposal.md`). Their sandbox's name has not resolved since Sep 23 (hl7-eu/oah issue 8), so the mirror cannot be read there today; the read-back of Sep 21 stands in.

## Usability and user experience (15%)

Our mark: partial. English only, and the form's wording waits on a check against the official app.


| What to look at | Where |
|---|---|
| No camera, any phone: the test takes about four minutes with its lesson | https://second-look-79t.pages.dev |
| One question per screen at the creek | `/check` |
| Reading age measured on every string in CI | `make readability` |
| Tap targets and contrast measured in CI | `make design-check` |

Thin: English only; a Spanish draft is not in the build.

## Feasibility and scalability (15%)

Our mark: strong. Free to run, a follower city scaffolds in seconds, and a city that reads OneAquaHealth records reads ours.


| What to look at | Where |
|---|---|
| OneAquaHealth's five steps for a follower city, set up for Berkeley the way a follower city would; no volunteer has been trained or tested and no real visit exists yet | README, Feasibility: set up for Berkeley the way a follower city would |
| A second city scaffold, its lists still to fill | `fhir/fsh/city-heraklion.fsh`; `content/regions/heraklion.yaml` |
| Free to run on Cloudflare, no card | `docs/notes/hosting.md` |
| The example offered back to their guide | `docs/ig_proposal.md` |

Thin: four photos per feature is coarse, and the photos come from open collections in several countries, not from the creek a Berkeley volunteer stands in.
