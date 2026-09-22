# Judge scorecard

The five criteria the organizers score, 1 to 10 each, with where to look for each one and what is still thin. Written for judges who have a few minutes. Every claim points at a file or a command, and nothing here is a result number: those live in `results/` and the README.

## Impact and alignment with the OneAquaHealth mission (30%)

| What to look at | Where |
|---|---|
| The problem, in the project lead's own words: volunteers miss built banks, dug-out channels and invasive plants | README, The problem |
| The score travels with every observation, as a Practitioner qualification under their profiles | `fhir/golden/visit-strawberry-creek-1.json`; `/spot` |
| City actions are OneAquaHealth's own restoration measures, from their Policy Brief (2026), page 9 | `/city?creek=strawberry-creek`; README |
| One action each for the person, the pet and the city, from approved sentences with sources | `content/approved_sentences.yaml`; the health card on `/spot` |

Thin: no recruited study, so no measured effect of the lesson on people. Said in Known weaknesses.

## Innovation and creativity (20%)

| What to look at | Where |
|---|---|
| A volunteer is tested per feature and the score is stored with the data, like a lab's quality checks | README, Innovation and practical value |
| The AI takes the same test and may only speak on a feature it passed | `core/gate.py`; `results/model_pass_table.json` |
| Follow-ups chosen by code from answers, scores and the weather, two at most | `core/followups.py`; `/check` |

Thin: the model results arrive with the paid run (`uv run python evals/model_sweep.py --real`).

## Technical implementation (20%)

| What to look at | Where |
|---|---|
| FHIR R4 against their guide at b907cf0, validated in CI, zero errors in the latest run | `results/fhir_validation.json`; `make fhir-validate` |
| Their sandbox mirrored with conditional creates, a tag on everything, a ledger of ids | `fhir/sandbox_ledger.jsonl`; `/two` |
| A read-only MCP server over our own records | `apps/mcp/server.py`; `examples/mcp/transcript.md` |
| One command, no key, no network | `make judge-check` |

Thin: the citizen observer is modelled as a Practitioner because R4 has no better fit; the question is open with the guide's authors (`docs/ig_proposal.md`).

## Usability and user experience (15%)

| What to look at | Where |
|---|---|
| Two minutes, no camera, any phone | https://second-look-79t.pages.dev |
| One question per screen at the creek | `/check` |
| Reading age measured on every string in CI | `make readability` |
| Tap targets and contrast measured in CI | `make design-check` |

Thin: English only; a Spanish draft is not in the build.

## Feasibility and scalability (15%)

| What to look at | Where |
|---|---|
| OneAquaHealth's five steps for a follower city, run on Berkeley | README, Feasibility |
| A second city scaffold, and a second plant list | `fhir/fsh/city-heraklion.fsh`; `content/regions/heraklion.yaml` |
| Free to run on Cloudflare, no card | `docs/notes/hosting.md` |
| The example offered back to their guide | `docs/ig_proposal.md` |

Thin: four photos per feature is coarse, and the photos come from open collections in several countries, not from the creek a Berkeley volunteer stands in.
