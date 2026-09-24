# Link check 00

Checked 2026-09-24T09:25:34Z at commit 21f6db0 by `uv run python scripts/harden_links.py`, over README.md and every tracked Markdown file under docs/ (57 files). Nothing was fixed. Raw rows: `results/harden/links.json`.

Relative links are resolved from the file that holds them and their #anchors are checked against the target's headings the way GitHub makes them. Paths in backticks are resolved from the repo root. Each web address got one GET with redirects followed. A site that answers 401, 403, 405, 429 or 999 to a script is listed as blocked, not dead: open it by hand. A path that git ignores (build output, local data) is listed as ignored, not dead. api.enora-oah.eu and the Resilience Map API were never called (hard rule 9); the HL7 sandbox got at most one GET a second and 50 in all (hard rule 10).

## Counts

| Kind | ok | dead | blocked | private | ignored | skipped |
|---|---|---|---|---|---|---|
| relative | 24 | 0 | 0 | 0 | 0 | 0 |
| backtick | 877 | 0 | 0 | 0 | 9 | 0 |
| url | 119 | 0 | 9 | 9 | 0 | 25 |

## Dead, in the README and product docs

None.

## Dead, in docs/internal (working notes)

None.

## Blocked, check by hand

| File and line | Kind | Link | What happened |
|---|---|---|---|
| README.md:429 | url | https://www.inaturalist.org/pages/terms | 403, the site refuses scripts |
| README.md:560 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/THIRD_PARTY.md:11 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/THIRD_PARTY.md:22 | url | https://www.inaturalist.org/pages/terms | 403, the site refuses scripts |
| docs/THIRD_PARTY.md:23 | url | https://www.inaturalist.org/pages/api+recommended+practices | 403, the site refuses scripts |
| docs/notes/sandbox_library.md:6 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/notes/sandbox_library.md:10 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/notes/sandbox_library.md:126 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/notes/sandbox_library.md:127 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |

## Skipped on purpose

| File and line | Kind | Link | What happened |
|---|---|---|---|
| README.md:13 | url | https://github.com/alejandro-publius/second-look/actions/workflows/check.yml/badge.svg | a name under our repo address, not a page |
| README.md:13 | url | https://github.com/alejandro-publius/second-look/actions/workflows/check.yml | a name under our repo address, not a page |
| README.md:520 | url | http://localhost:3100 | local or example address |
| README.md:520 | url | http://localhost:3100/city?creek=strawberry-creek | local or example address |
| docs/ig_proposal.md:89 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:45 | url (in code) | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:46 | url (in code) | http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:100 | url | http://hl7.org/fhir/StructureDefinition/DomainResource | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:104 | url | http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType%7C3.0.0 | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:104 | url | http://snomed.info/sct#420531007 | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:160 | url (in code) | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:178 | url | http://hl7.eu/fhir/ig/oah/ValueSet/oah-indicators-no-health-oah-vs | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:178 | url | https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look#artificial-bank | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:22 | url (in code) | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-oah | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:33 | url (in code) | http://www.w3.org/1999/xhtml\ | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:37 | url (in code) | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-size | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:44 | url (in code) | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-numberOfRecords | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:48 | url (in code) | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:51 | url (in code) | https://github.com/alejandro-publius/second-look/fhir/library-id | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:62 | url (in code) | http://terminology.hl7.org/CodeSystem/library-type | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:90 | url (in code) | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/notes/sandbox_library.md:107 | url (in code) | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:109 | url (in code) | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:110 | url (in code) | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
| docs/submission/JUDGE_QA.md:92 | url | https://github.com/alejandro-publius/second-look/actions | a name under our repo address, not a page |
