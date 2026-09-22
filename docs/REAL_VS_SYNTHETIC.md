# What is real and what is synthetic

One list, kept current, so nobody has to guess. The README's "What is real and what is
synthetic" section (Update 10 tier 3 item 10) is built from this file after data lock. Until then
this is the list. A thing is **real** when it was produced by the system from a person's action or
from a live source. It is **synthetic** when a script made it up to show a shape. It is an
**example** when it is a hand shaped instance that stands in for a real one and is marked as such.

| Thing | Status | How you can tell | Where |
|---|---|---|---|
| The two minute test flow, its randomization and its scoring | real | code and tests; nothing is faked in the flow | `apps/web`, `worker/src/index.ts`, `core/allocator.py`, `core/scoring.py` |
| The photographs in the test | synthetic placeholders until Alex's picks land on `main` | every row in the manifest is `license: placeholder` | `photos/manifest.csv` |
| Study results in the README | none yet | the results section shows no table until the model run; the synthetic dry runs stay in `results/` with SYNTHETIC on every file and none of their numbers appears in the README | `README.md`, `scripts/verify_claims.py` |
| The model pass table | synthetic | `"real": false` in the file; the checker refuses to flag on it | `results/model_pass_table.json`, `core/checker.py` |
| A creek check, its follow-ups and its record | real once a person files one | stored visit, FHIR Bundle in the store, audit line | `apps/api/check.py`, `data/fhir_store/` |
| The golden Strawberry Creek visit Bundle | example, hand shaped from a worked visit | it is in `fhir/golden/` and not in the store | `fhir/golden/visit-strawberry-creek-1.json` |
| The referral: a ServiceRequest for a pipe worth testing | real, computed on request from stored visits | it exists only for a pipe two people who passed saw running in dry weather, and it is never stored | `core/fhir_referral.py`, `GET /api/fhir/referral/{spot_id}` |
| The laboratory result coming back to that record | example | every laboratory resource carries `meta.tag` `example`, its narrative starts with EXAMPLE, the screen shows a badge and a notice, and no number on `/city` counts it | `core/fhir_referral.py`, `GET /api/fhir/referral/{spot_id}/example-result` |
| The golden referral and example result Bundles | example, built from two synthetic visits | in `fhir/golden/`, validated in CI, never in the store | `fhir/golden/referral-strawberry-creek-1.json`, `fhir/golden/example-lab-result-strawberry-creek-1.json` |
| The laboratory Observation beside ours on `/two` | real, read from their sandbox | `theirs_status` says `ok`, `cached` or `down`; the cache lives in `data/`, never in git | `apps/api/fhir_routes.py` |
| The sandbox mirror and its ledger | real, one write proven on 2026-09-20 | `fhir/sandbox_ledger.jsonl` | `scripts/repush_sandbox.py` |
| Rainfall behind the dry pipe question | real, from Open-Meteo, or unknown | `site_json.source` on the visit says `open-meteo` or `unknown` | `core/rainfall.py` |
| The consensus and power figures | synthetic | files carry `"synthetic": true` and the SYNTHETIC stamp | `results/` |
| The Heraklion follower city scaffold | example, dry run in English with no claims | the checklist says so in its first line | `docs/cities/heraklion/` |

Rules this list follows:

- A synthetic or example thing is never counted in any number a person sees.
- A synthetic result is never cited without `--synthetic`, and never after data lock.
- An example resource in FHIR is tagged in `meta.tag` and says EXAMPLE in its narrative, so it
  stays an example even when copied out of this repository.
