# 0005. Records are FHIR under OneAquaHealth's profiles, with a pseudonymous Practitioner

- **Status:** accepted
- **Date:** 2026-09-20
- **Carried by:** commit f84d786 (the FHIR proof against their profiles passes) and commit
  00ffea4 (the emitter, the golden records and the store); `core/fhir_emit.py`, `fhir/ig.lock`,
  `fhir/fsh/`, `docs/fhir_mapping.md`, `scripts/fhir_validate.py`, `docs/ig_proposal.md`

## Context

OneAquaHealth wants citizen observations to stand beside laboratory data under the same profiles
and value sets. Their guide has profiles for locations and indicator observations, but none for the
person who observed, for a questionnaire, or for provenance. The observer must stay pseudonymous:
no name, and no token that could be used to act as them.

## Decision

Use their profiles and codes wherever they exist (`LocationOah`, `ObservationIndicatorsOah`, their
value sets and UCUM units) and base FHIR R4 4.0.1 elsewhere. The volunteer is a `Practitioner`
known only by a hash of a random contributor token, with one qualification: the Second Look test,
dated, valid for 90 days, issued by our Organization. The test sitting's per-feature score is a
QuestionnaireResponse, and a `Provenance` ties every Observation to the person and to that sitting.
The guide is pinned to hl7-eu/oah b907cf0 in `fhir/ig.lock`, and sample records from both emitters
are checked by the HL7 validator in CI, terminology on; golden vectors hold the live emitter to them.

## Consequences

- A city that reads OneAquaHealth records can read ours, and the score of the person behind each
  answer travels with it.
- A volunteer is not really a practitioner. We say so, with two other gaps our validator runs found,
  in `docs/ig_proposal.md`, whose FSH builds inside their guide in CI.
- A new code goes in two places, `core/fhir_emit.py` and `fhir/fsh/codesystem-second-look.fsh`, or
  the emitter test fails on purpose.
- The contributor token itself never appears in a record
  (`core/tests/test_fhir_emit.py::test_the_contributor_token_itself_never_appears_in_the_record`).
