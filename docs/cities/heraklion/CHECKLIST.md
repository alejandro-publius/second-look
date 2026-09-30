# Heraklion, Greece: a follower city checklist

**A dry example in English. No claims.** Nobody has run Second Look in Heraklion. Nothing in this
folder is a finding about any creek. It was written by `scripts/new_city.py` on 2026-09-30 from a
name and one pair of coordinates (35.3387, 25.1442), to show that a new city is a checklist, not a
rebuild. OneAquaHealth calls a city that adopts the method a follower city and gives five steps.
Each step below names the files and commands in this repository that do it.

## 1. Name the streams

- [ ] Rename the placeholder creek, reach and spot in `fhir/fsh/city-heraklion.fsh` and add a
      Location per real creek, reach and spot, each `partOf` the one above.
- [ ] Fill `creeks:` in `content/regions/heraklion.yaml`: a readable slug per creek, its reaches
      from the hills down, `flows_into` on each, an approximate box from public maps.
- [ ] `bash scripts/fhir_build.sh` builds the guide with the new Locations inside it;
      `make check` runs the HL7 validator over the Bundle.

## 2. Adopt the form

- [ ] The creek check mirrors the official Citizen Science App in `content/form.yaml`. Check
      each item's wording against the app in the city's language; set `verified_against_app`.
- [ ] The two minute test and its scores are already a Questionnaire and a
      QuestionnaireResponse in `fhir/fsh/questionnaires-second-look.fsh`. Nothing to add.
- [ ] A new language is a file in `content/locales/`, shipped only with a named fluent checker
      recorded in it (PLAN.md, COULD list).

## 3. Train and test the volunteers

- [ ] About 40 local photos per the shot list, own or openly licensed, no faces or plates:
      `scripts/find_open_photos.py`, then `scripts/ingest_photos.py`.
- [ ] Two people label the 16 test photos blind through `scripts/label_photos.py`;
      `scripts/merge_labels.py` prints Cohen's kappa and refuses to freeze while they disagree.
- [ ] Fill `invasive_plants:` in `content/regions/heraklion.yaml` from the regional inventory,
      with the source named.
- [ ] Set `bbox:` at the top of that file, [south, west, north, east] in degrees from public
      maps. The plant list is offered only to a pin inside this box; while it is null, no pin
      in Heraklion is offered the list.
- [ ] `scripts/freeze_key.py`, then the lesson checked on strangers before launch.

## 4. Collect and validate

- [ ] Every visit becomes Observations under their indicator profile with Provenance back to
      the observer's score: `core/fhir_emit.py`, nothing to change.
- [ ] `make check` validates every emitted record in CI before it is stored or mirrored.
- [ ] Print `docs/cities/heraklion/poster.html` on Letter or A4 once two local photos are in.
      Its QR opens https://second-look-79t.pages.dev. Pass `SITE=` to `make new-city` to point it at
      your own site. The poster's words are English.

## 5. Publish and repeat

- [ ] Mirror records to the sandbox with the tag and the ledger:
      `scripts/repush_sandbox.py`.
- [ ] Register the city's Library entry there: `scripts/repush_sandbox.py --library`.
- [ ] Return visits through the quick check, so one snapshot becomes a story.

## What this scaffold did not do

It did not choose any creek, place any pin, name any plant or state anything about the water.
Those are the city's to fill in, by hand, with sources.
