Title: Example: a citizen observer's test score carried with their observations (Second Look, Berkeley)

Hello from the Second Look team in Berkeley, a follower city. This pull request adds one worked example to the guide and asks one question. It changes no profile.

## What it adds

`input/fsh/second-look/`, five FSH files built from our project (MIT):

- `codesystem-second-look.fsh`: our local CodeSystem for the four features your value sets do not name yet (built banks, dug-out channel, invasive plants, pipes and outlets), plus `cant-tell`.
- `questionnaires-second-look.fsh`: two Questionnaires, the two-minute observer test and the creek check. The check follows your Citizen Science App's items in order, with stable linkIds.
- `example-visit-second-look.fsh`: one complete visit at Strawberry Creek. Nested Locations under `LocationOah`, Observations under `ObservationIndicatorsOah`, a pseudonymous Practitioner with a dated qualification that holds the observer's test score, and a Provenance from each Observation to the visit and to the test sitting.
- `city-heraklion.fsh`: a scaffold of nested Locations for a second follower city, to show the shape travels.
- `aliases-second-look.fsh`: aliases the files above use.

<!-- claim: results/fhir_validation.json#/errors = 0 -->
SUSHI 3.20.1 builds it inside the guide at b907cf0 with no errors, and the HL7 validator reports 0 errors on the result.

## What we found (friendly notes)

1. There is no profile for the person who observes, and none for Provenance or QuestionnaireResponse, so the part of a citizen record that says who looked and how good they are at looking falls back to plain R4.
2. We modelled a citizen volunteer as a pseudonymous Practitioner, because `Observation.performer` has no better fit. It carries one qualification and a random token, no name, telecom, address, birth date or gender.
3. `SpecimenOah.collection.collector` allows only `Reference(PractitionerRole)`. A laboratory is an Organization, and a trained volunteer taking a sample is closer to a Practitioner.
4. Your temporary code system spells one code `morophology`. We kept it so our records validate. You may want to correct it before other cities copy it.

## The one question

Which resource should stand for a citizen observer? If it is Practitioner, it would help if the guide said so. If you prefer RelatedPerson, Patient or a Device for an app account, tell us and we will change ours.

## What we would be glad to add next, if you want it

- A qualification pattern for citizen observers: a code from a small ValueSet of observer tests, a required period so every score has an end date, and the issuer.
- A Provenance pattern for citizen Observations: author the person, assembler the software, source the visit response and the test sitting.
- A note beside the `preferred` binding on `ObservationIndicatorsOah.code` inviting follower cities to publish local codes for features the value set does not yet name.
- A wider `SpecimenOah.collection.collector` and a small ServiceRequest pattern for the step from a citizen finding to a sample.

The full write-up, with every validator message, is in our repository: https://github.com/alejandro-publius/second-look/blob/main/docs/ig_proposal.md

Thank you for the guide. It made this possible.
