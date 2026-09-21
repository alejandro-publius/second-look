# Proposal: carrying observer quality for citizen data in the OneAquaHealth guide

For the authors of hl7-eu/oah. Written by the Second Look team (Berkeley, a follower city). One page, plain words. Alex opens the pull request; this file is the text behind it.

## The problem in one line

Professional surveyors pass a test before their data counts. Citizen observers never have. The guide has a profile for an indicator Observation and a profile for a Location, but no place to say how good the person who made the observation is at seeing that indicator.

## What we did

Every volunteer takes a two minute photo test on four stream features (built banks, dug-out channel, invasive plants, pipes and sewage signs), four photos per feature, scored by code as k of 4. Every creek check they make afterwards is stored as FHIR R4 (4.0.1) under your profiles, with that score attached to the person and reachable from every Observation.

## What we stored and where

One visit becomes one collection Bundle (example: `fhir/golden/visit-strawberry-creek-1.json`, built by `core/fhir_emit.py`):

| Resource | Profile | What it holds |
|---|---|---|
| Location, three nested | your `LocationOah` | creek, reach (`partOf` creek), spot (`partOf` reach, with `position`) |
| Practitioner | base R4 | the volunteer, identified only by a random contributor token. One `qualification` coded `second-look-test`, `period` from the test date to 90 days later, `issuer` our Organization |
| QuestionnaireResponse, test sitting | base R4 | one item per feature with the score out of 4 |
| QuestionnaireResponse, visit | base R4 | one item per answered check item, linkIds are the stable ids of the check form |
| Observation, one per answered item | your `ObservationIndicatorsOah` | `status final`, `subject` the spot, `performer` the Practitioner, `effectiveDateTime`, `derivedFrom` the visit response, a coded or quantity value |
| Provenance | base R4 | `target` every Observation, `agent` author = Practitioner and assembler = our software Device, `entity` source = the visit response and the test sitting |

The same Bundle also exists as a transaction of conditional creates (`fhir/golden/visit-strawberry-creek-1.transaction.json`) with our `meta.tag` on every resource, which is what we mirror to the sandbox.

## Why that shape

- The score belongs to the person, not to the observation, so it lives on the Practitioner as a dated qualification. A reader who finds any Observation follows `performer` to the Practitioner and sees the qualification and its period. When the period ends the score is expired and the volunteer retakes the test.
- The raw numbers live in the test sitting QuestionnaireResponse, so nothing is a blended grade or a probability. A city can decide its own threshold.
- Provenance is the path from an answer to the evidence for it: the visit response (what was asked and answered) and the test sitting (how well this person sees this feature). The software that assembled the record is named as an agent, so a reader knows no model wrote the answers.
- Your codes wherever they exist: `present`, `absent`, the indicator groups (`morophology`, `hydrology`, `invasiveOrganisms`, `foam`, `LandUse`, `riparianVegetation`) and the vegetation types. Ours only where you have none: the four feature codes, `cant-tell`, and the coded form answers (channel form, flow, habitats, debris, overall rating). Your `preferred` binding on `Observation.code` lets a local code through with an information note, which is exactly right for a follower city.
- Nothing here needed a change to your profiles. The record validates as is.

## What the validator said

HL7 validator 6.10.4, FHIR 4.0.1, your guide built from commit b907cf0 with our FSH inside it, terminology server off (so UCUM units cannot be checked). From `results/fhir_validation.json`:

```
fhir-validate: 3 file(s), 0 error(s), 17 warning(s), terminology checks off; details in results/fhir_validation.json
```

The three files are the FSH example Bundle SUSHI builds from `fhir/fsh/` and the two golden Bundles the emitter produces. Every warning is one of two kinds: the dom-6 "a resource should have narrative" best practice note on the FSH example, and "Unable to validate code 'm' in system http://unitsofmeasure.org because the validator is running without terminology services". The emitter's Bundles carry a generated narrative on every resource, so they show only the UCUM note. The `preferred` binding on `Observation.code` produced information notes for our local codes, not errors.

## The FSH example

`fhir/fsh/` holds our CodeSystem (`second-look`), two ValueSets (feature codes, answer values), the two Questionnaires (the observer test and the creek check, the second generated from our form so every linkId and answer option matches) and one complete visit example. `scripts/fhir_build.sh` copies them into `input/fsh/second-look/` inside a copy of your guide at the pinned commit and runs SUSHI 3.20.1: 0 errors, 0 warnings.

## What we would add to the guide

1. A Practitioner qualification pattern for citizen observers: `qualification.code` from a small ValueSet of observer tests, `qualification.period` required so every score has an end date, `qualification.issuer` the organisation that ran the test. The Practitioner carries an identifier and no name, so citizen records stay pseudonymous.
2. A Provenance pattern for citizen Observations: `target` the Observations of one visit, `agent` with `author` (the person) and `assembler` (the software), `entity` with `source` pointing at the QuestionnaireResponse of the visit and at the response that holds the person's test result. One Provenance per visit keeps the resource count small.
3. A note beside the `preferred` binding on `ObservationIndicatorsOah.code` saying that follower cities may use local codes for features your value set does not yet name, and asking them to publish the CodeSystem, as we do.
4. Optional: a `QuestionnaireResponse` profile for the observer test with one group per indicator and an integer score item, so cities can compare observer quality across countries with the same shape.

We would be glad to send the FSH for any of these as a pull request.
