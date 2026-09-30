# FHIR mapping: how one creek visit becomes a OneAquaHealth record

Proof P2 passed on 2026-09-20. The HL7 validator (6.10.4, FHIR 4.0.1) checked our complete visit Bundle against the OneAquaHealth guide built from hl7-eu/oah at commit b907cf0 with our additions inside it: 0 errors, 15 warnings. Every warning is either the "a resource should have narrative" best practice note (14) or the UCUM unit check that cannot run without a terminology server (1). Rerun with `make fhir-validate`. The evidence is `results/fhir_validation.json`.

## What one visit produces

| Resource | Profile | What it holds |
|---|---|---|
| Location, three nested | their `LocationOah` | creek, then reach (`partOf` creek), then spot (`partOf` reach, with `position`). Each has an identifier, a name and `mode = instance`, as the profile requires. |
| Practitioner | base R4 | the volunteer, identified only by a random contributor token. One `qualification` coded `second-look-test`, `period` from the test date to 90 days later, `issuer` our Organization. |
| QuestionnaireResponse, test sitting | base R4 | one item per feature with the score out of 4, computed by code. Authored by the Practitioner. |
| QuestionnaireResponse, visit | base R4 | one item per answered check item. Link ids are the stable ids from `content/form.yaml`. `language` is the language the questions were shown in, one of the official app's (UPDATE_32); the narrative is written in English and marked `lang="en"`, and says the language when it is not English, so the validator notes on those records that the two differ, which is true. |
| Observation, one per answered item | their `ObservationIndicatorsOah` | `status final`, `subject` the spot, `performer` the Practitioner, `effectiveDateTime`, `derivedFrom` the visit response, a coded or quantity value. |
| Provenance | base R4 | `target` every Observation of the visit, `agent` author = Practitioner and assembler = our software Device, `entity` source = the visit response and the test sitting. This is the path from any answer to the score of the person who gave it. |
| Organization, Device | base R4 | us, and the software. |
| Bundle, type collection | base R4 | everything above. The emitter also produces a transaction Bundle with conditional creates for the sandbox mirror (`to_transaction` in `core/fhir_emit.py`). |

## Codes: theirs where they exist, ours where they do not

- `Observation.value`: their `TemporaryOahSystem#present` and `#absent`. "Can't tell" is our `second-look#cant-tell` because their system has no general unknown code.
- `Observation.category`: their indicator groups. Built banks and dug-out channel sit under `#morophology` (their spelling), invasive plants under `#invasiveOrganisms`, pipes and water height under `#hydrology`. The profile does not bind category, so this is additive.
- `Observation.code`: our feature codes `artificial-bank`, `dug-out-channel`, `invasive-plant`, `pipe-running`. Their profile binds code to `OahIndicatorsNoHealthOahVs` with strength `preferred`, so a code outside it produces an information note, not an error. The validator confirmed this. Water height uses their own `#hydrology` code directly.
- Coding displays must be the code system's own display. The words a person sees on screen live in `content/form.yaml`, never in the coding.
- Units are UCUM (`m` for water height).

## What a record calls itself

- `Observation.code.text` and the narrative say what was found and keep the app's own name for the question beside it in brackets, as in `Artificial bank (Bank Type)`. For an item on one of our feature codes the finding is that code's display. For the other yes or no items it is a short phrase kept in `content/form.yaml` under `fhir.finding`. An item with other answers, such as Water Flow, is named by the app alone. The rating Observation, which exists only when the rating check changed the rating, is named by its code's display, `Overall rating`, because the app has no short name for that question; the question is in the Questionnaire the visit response names.
- In the narrative each coded value reads as its display does, such as `Present` or `Can't tell`. The values of a list are parted by a semicolon, because a display may hold a comma.
- Several items share one group code. Channel form, bottom type, habitats, natural debris, barriers and construction all carry `#morophology` as `Observation.code`. They are told apart by `code.text` and by the identifier, which ends in the form item id. Answer options that map to the same value are not kept apart: muddy water, foam and a changed colour are all stored as `present`.

## What the validator said, in plain words

- Our Observations conform to their indicator profile, including the fixed `status`, the required `subject` that must be one of their Locations, and the required `performer`.
- Our Locations conform to their Location profile, including the nesting.
- The `preferred` binding on `Observation.code` accepts our local codes with an information note.
- Nothing in their guide blocks a citizen record. There is no gap that is theirs to fix, so fallback F2 (plain R4 without their profiles) is not needed.

## What their guide does not have, and what we add

Their guide has no Questionnaire, QuestionnaireResponse, Provenance or Practitioner profile, and no citizen example. We use base R4 for those and propose the shape in `docs/ig_proposal.md` (W3). Our CodeSystem and two ValueSets are in `fhir/fsh/` and build inside a copy of their guide with `scripts/fhir_build.sh`.

## Pins

`fhir/ig.lock` holds the guide commit, the SUSHI version (3.20.1), the validator version and download URL, Node 20 and Java 17. CI builds the guide from source and never commits the package, because their repo has no LICENSE file.
