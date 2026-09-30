# P2: the full HL7 validator run, with terminology checking on

P2 asks: will their profiles accept a citizen record with an observer score?
This note records the run that answers it. Every message below is copied word
for word from the validator output.

## 1. What was run

Two runs. Run A is the P2 run. Run B only puts the repo back to its normal
state so `make check` stays reproducible.

**Run A, terminology checking ON (this is the P2 run).**

```
export JAVA17_HOME=/opt/homebrew/opt/openjdk@17
uv run python scripts/fhir_validate.py --no-build --tx https://tx.fhir.org
```

That script shells out to the jar like this:

```
java -Xmx3g -jar fhir/tools/validator_cli.jar \
  fhir/build/ig/fsh-generated/resources/Bundle-sl-visit-1-bundle.json \
  fhir/golden/visit-strawberry-creek-1.json \
  fhir/golden/visit-strawberry-creek-1.transaction.json \
  -version 4.0.1 \
  -ig fhir/build/ig/fsh-generated/resources \
  -tx https://tx.fhir.org \
  -output fhir/build/validation_outcome.json
```

- Validator: `FHIR Validation tool Version 6.10.4 (Git# 1b90fb13f77b). Built 2026-09-04T05:45:41.468Z`
- Java: `17.0.20.1` from Homebrew openjdk@17
- FHIR version: R4 4.0.1
- Their guide: `hl7-eu/oah` at pinned commit `b907cf0`, built by SUSHI 3.20.1.
  The validator log line was `Load ~/second-look/fhir/build/ig/fsh-generated/resources - 510 resources (00:00.198)`.
- Terminology: **it ran.** The log line was
  `Terminology server https://tx.fhir.org - Version Connected to Terminology Server at https://tx.fhir.org (00:01.104)`.
- When: 2026-09-21 02:59 UTC. The whole run took about 14 seconds.
- Result line: `fhir-validate: 3 file(s), 0 error(s), 23 warning(s), terminology checks ran; details in results/fhir_validation.json`

**Proof the terminology server really did work, not just connect.** Compare
with the old terminology-off run:

- Off: `Unable to validate code 'm' in system 'http://unitsofmeasure.org' because the validator is running without terminology services`. On: that message is gone, so UCUM `m` was checked and passed.
- Off: `Could not confirm that the codes provided are from the extensible value set http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType because there is no terminology service` at information level. On: the value set was expanded and the code was judged, and the message became a real warning.

So terminology-off was leaving 12 checks unanswered: 9 value set checks it
could not run, and 3 UCUM codes it could not read. With the server on, the 9
became real warnings and the 3 UCUM warnings cleared, which is why the total
moved from 17 to 23. None of the 12 turned into an error.

**Run B, terminology off, to restore the repo default.**

```
uv run python scripts/fhir_validate.py --no-build
```

That writes `results/fhir_validation.json` back to the normal
`-tx n/a` state: 3 files, 0 errors, 17 warnings, byte for byte the same as the
run recorded in `docs/ig_proposal.md` apart from the timestamp. The 23 warning
numbers in this note come from Run A only.

**Landmine worth knowing.** Run A leaves a terminology cache at
`$TMPDIR/default-tx-cache`. If you then run with `-tx n/a` while that cache is
warm, the validator answers value set questions from the cache and reports 26
warnings, not 17. That silently breaks the number quoted in
`docs/ig_proposal.md`. Delete `$TMPDIR/default-tx-cache` before the restoring
run. This note's Run B was done after deleting it.

## 2. The instance set, checked against P2's list

P2 asks for a smallest set that carries the idea. The set lives in
`fhir/build/ig/fsh-generated/resources/Bundle-sl-visit-1-bundle.json` (built by
SUSHI from our FSH) and again in `fhir/golden/visit-strawberry-creek-1.json`
(written by our emitter). Both were validated.

| P2 asked for | Found | Notes |
|---|---|---|
| Three nested Locations | Yes | `sl-loc-strawberry-creek`, then `sl-loc-campus-reach` with `partOf` the creek, then `sl-loc-spot-1` with `partOf` the campus reach. All three claim `location-oah`. |
| Pseudonymous Practitioner with one qualification | Yes | `sl-practitioner-1` has exactly one `qualification` entry (code `second-look-test`, period 2026-09-23 to 2026-12-22, issuer `Organization/sl-org`). No `name`, no `telecom`, no `address`, no `birthDate`, no `gender`. The only identifier is a random contributor token `ct_7f3a9c2e` on our own system. Nothing in it can name a person. |
| One test QuestionnaireResponse with per-feature scores | Yes | `sl-qr-test-1`, four items, one integer score per feature. |
| One visit QuestionnaireResponse | Yes | `sl-qr-visit-1`, five answers. |
| Two Observations under their Observation profile | Yes, five | `sl-obs-bank-1`, `sl-obs-channel-1`, `sl-obs-invasive-1`, `sl-obs-pipe-1`, `sl-obs-water-height-1`, all claiming `observation-indicators-oah`. Five is more than the two P2 asked for, so the line is met. |
| One Provenance that links an Observation to both responses | Yes | `sl-provenance-visit-1` targets all five Observations and carries two `entity` items, both `role: source`: `QuestionnaireResponse/sl-qr-visit-1` and `QuestionnaireResponse/sl-qr-test-1`. |

Nothing was changed to make this pass. No instance was edited during this run.

The golden bundle mirrors the same shape with emitter-generated ids, and its
Provenance also points at both responses.

## 3. Every error and warning, word for word, grouped by resource

**Errors: none. Zero errors in all three files.**

23 warnings. There are only two distinct warning texts.

Text A:

> Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)

Text B:

> None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (codes = http://snomed.info/sct#420531007)

Now every warning, grouped by the resource it landed on.

### Organization/sl-org
- `Bundle.entry[0].resource/*Organization/sl-org*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### Device/sl-device
- `Bundle.entry[1].resource/*Device/sl-device*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### Location/sl-loc-strawberry-creek
- `Bundle.entry[2].resource/*Location/sl-loc-strawberry-creek*/.type[0]` in `Bundle-sl-visit-1-bundle.json`: Text B.
- `Bundle.entry[2].resource/*Location/sl-loc-strawberry-creek*/` in `Bundle-sl-visit-1-bundle.json`: Text A.
- `Bundle.entry[2].resource/*Location/sl-loc-strawberry-creek*/.type[0]` in `visit-strawberry-creek-1.json`: Text B.
- `Bundle.entry[2].resource/*Location/null*/.type[0]` in `visit-strawberry-creek-1.transaction.json`: Text B. (The id reads `null` because that entry is a POST with `ifNoneExist=Location?identifier=...|strawberry-creek`, so it has no id yet. It is the same creek Location.)

### Location/sl-loc-campus-reach
- `Bundle.entry[3].resource/*Location/sl-loc-campus-reach*/.type[0]` in `Bundle-sl-visit-1-bundle.json`: Text B.
- `Bundle.entry[3].resource/*Location/sl-loc-campus-reach*/` in `Bundle-sl-visit-1-bundle.json`: Text A.
- `Bundle.entry[3].resource/*Location/sl-loc-campus-reach*/.type[0]` in `visit-strawberry-creek-1.json`: Text B.
- `Bundle.entry[3].resource/*Location/null*/.type[0]` in `visit-strawberry-creek-1.transaction.json`: Text B. (POST entry for the campus reach.)

### Location/sl-loc-spot-1
- `Bundle.entry[4].resource/*Location/sl-loc-spot-1*/.type[0]` in `Bundle-sl-visit-1-bundle.json`: Text B.
- `Bundle.entry[4].resource/*Location/sl-loc-spot-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.
- `Bundle.entry[4].resource/*Location/sl-loc-spot-1*/.type[0]` in `visit-strawberry-creek-1.json`: Text B.
- `Bundle.entry[4].resource/*Location/null*/.type[0]` in `visit-strawberry-creek-1.transaction.json`: Text B. (POST entry for spot 1.)

### Practitioner/sl-practitioner-1
- `Bundle.entry[5].resource/*Practitioner/sl-practitioner-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

Nothing else. No warning about the missing name, the contributor token, or the
single qualification.

### QuestionnaireResponse/sl-qr-test-1
- `Bundle.entry[6].resource/*QuestionnaireResponse/sl-qr-test-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### QuestionnaireResponse/sl-qr-visit-1
- `Bundle.entry[7].resource/*QuestionnaireResponse/sl-qr-visit-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### Observation/sl-obs-bank-1
- `Bundle.entry[8].resource/*Observation/sl-obs-bank-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### Observation/sl-obs-channel-1
- `Bundle.entry[9].resource/*Observation/sl-obs-channel-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### Observation/sl-obs-invasive-1
- `Bundle.entry[10].resource/*Observation/sl-obs-invasive-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### Observation/sl-obs-pipe-1
- `Bundle.entry[11].resource/*Observation/sl-obs-pipe-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### Observation/sl-obs-water-height-1
- `Bundle.entry[12].resource/*Observation/sl-obs-water-height-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

With terminology off this Observation also drew
`Unable to validate code 'm' in system 'http://unitsofmeasure.org' because the validator is running without terminology services`.
With terminology on that message is gone. The UCUM metre passed.

### Provenance/sl-provenance-visit-1
- `Bundle.entry[13].resource/*Provenance/sl-provenance-visit-1*/` in `Bundle-sl-visit-1-bundle.json`: Text A.

### Count check

14 Text A warnings plus 9 Text B warnings is 23, which matches the run line.
Text A only ever hits `Bundle-sl-visit-1-bundle.json`, the hand-written FSH
example. Our emitter output already writes a narrative, so it draws no Text A
at all.

### One information message worth reading

Not a warning, but it is the message P2 was most worried about, so it is
recorded here word for word:

> None of the codings provided are in the value set 'OAH Indicators (Non-Health)' (http://hl7.eu/fhir/ig/oah/ValueSet/oah-indicators-no-health-oah-vs), and a coding is recommended to come from this value set (codes = https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look#artificial-bank)

The same message appears for `dug-out-channel`, `invasive-plant` and
`pipe-running`. It is information, not an error, because
`observation-indicators-oah` binds `Observation.code` at strength
**preferred**. A preferred binding does not reject our codes.

## 4. Verdict

**PASS.**

Zero errors on our instances with terminology checking on against
`https://tx.fhir.org`. None of P2's three fail conditions fired. Their
`observation-indicators-oah` profile requires only `subject`, `effective[x]`
and `performer`, all of which we fill honestly: `subject` must point at a
`location-oah`, which is the creek spot, not a patient; `performer` has no type
restriction, so a Practitioner is accepted; `Observation.code` is bound only at
preferred strength, so our four feature codes are allowed with no invented
extension. The 23 warnings are a missing narrative on the hand-written example
bundle, which we can add on our side, and an extensible binding on
`Location.type` where a SNOMED creek code is not in a value set of health care
delivery sites, which the binding itself permits.

No ig_gap_report.md is written, because the verdict is not FAIL.

## 5. Two honest caveats, neither of them a fail

- We model a citizen volunteer as a `Practitioner`. The validator accepts it,
  and the guide at `b907cf0` has no Practitioner profile at all, so nothing
  in their guide pushes back. It is still a modelling choice worth raising with
  the guide's authors, not a validator finding.
- The guide at `b907cf0` also has no profile for `QuestionnaireResponse` or
  `Provenance`. Those two resources were validated as plain R4. So P2's answer
  is precise: their Location and Observation profiles accept a citizen record.
  They say nothing yet about where the observer score itself should live.
