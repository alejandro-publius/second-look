# What is real and what is synthetic

One list, kept current, so nobody has to guess. The README's "What is real and what is
synthetic" section (Update 10 tier 3 item 10) is built from this file after data lock. Until then
this is the list. A thing is **real** when it was produced by the system from a person's action or
from a live source. It is **synthetic** when a script made it up to show a shape. It is an
**example** when it is a hand shaped instance that stands in for a real one and is marked as such.

| Thing | Status | How you can tell | Where |
|---|---|---|---|
| The two minute test flow, its randomization and its scoring | real | code and tests; nothing is faked in the flow | `apps/web`, `worker/src/index.ts`, `core/allocator.py`, `core/scoring.py` |
| The photographs in the test | real, openly licensed, from several countries | every row in the manifest names its source page, author and licence, and no row says `placeholder` | `photos/manifest.csv` |
| The frames from open creek footage | real, cut from openly licensed video | role `benchmark` in the manifest, with the source video and the second it was taken at | `photos/benchmark/`, `videos/manifest.csv` |
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
| The simulation of weighted votes quoted under Known weaknesses in the README | synthetic by design: made-up people, never a study result | the file carries `"synthetic": true` and the SYNTHETIC stamp, the README sentence calls it a simulation, and `make consensus-check` reruns it | `results/consensus_coarseness.json`, `evals/consensus_coarseness.py` |
| The screen that keeps a frame | real, run on this Mac | Apple Vision (people, faces, any readable text, a water label, blank frames) and OpenCV; every drop and its reason is in `videos/frames.json` | `scripts/make_frames.py` |
| A video walk's record | real shape, demo content | made on the phone from the person's answers, every resource tagged `demo-walk`, never stored, counted or mirrored | `core/walks.py`, `worker/src/core/walks.ts`, `/walk/<id>` |
| The checker's flags on a walk | synthetic until the model run | worked out at build time from `results/footage_latest.json`; a footage run that is not real gives no flag at all, and a pass table from the fake client licenses none, so no walk asks a question yet | `scripts/build_walks.py`, `content/walks.yaml` |
| The Heraklion follower city scaffold | example, dry run in English with no claims | the checklist says so in its first line | `docs/cities/heraklion/` |

## Where a frame's label comes from, and where it does not

This is the method, written out, because it is the weakest joint in the footage work and hiding
it would be dishonest.

A frame is cut from a video whose own title and description we can read. The label for that
frame comes from the uploader's own words, and only from them. `scripts/pick_videos.py` looks for
a short list of phrases, `LABEL_RULES`, first in the description and then in the title, and the
evidence says which of the two it quotes. These are all of the phrases, and a test checks that
this list and the code stay the same:

- **artificial_bank present** when the words include any of `concrete channel`,
  `concrete flood channel`, `concrete-lined`, `concrete lined`, `lined with concrete`,
  `concrete culvert`, `culverted`, `flood channel`, `storm channel`, `encased in concrete`,
  `concrete banks`, `concrete walls`, `riprap`, `rip-rap`, `rip rap`, `gabion` or
  `retaining wall`. A concrete flood channel is a built bank. That is the one inference we allow
  ourselves, and we allow it because the words are the uploader's, not ours.
- **dug_out_channel present** when they include any of `straightened`, `channelized`,
  `channelised`, `canalised`, `canalized`, `dug out` or `trapezoidal channel`.
- **dug_out_channel absent** when they include any of `wild and scenic`, `free-flowing`,
  `free flowing` or `unmodified channel`.
- **pipe_running present** when they include any of `outfall`, `storm drain outlet`,
  `discharge pipe` or `sewer outlet`, in the sense our test uses, which is that a pipe or outfall
  is visible.
- No plant label ever comes from a description, or from a title: there is no phrase for
  **invasive_plant** at all. A species identification needs the plant in front of someone who
  knows it, and our own rule is that a plant we call invasive must be on the Cal-IPC inventory
  with a link. A video description cannot meet that.
- Everything else is **unlabelled**. An unlabelled frame is never scored for accuracy. It is used
  only to ask whether the three models agree with each other, which is a question that needs no
  key.

What this method is not:

- It is **not a gold standard**. Nobody stood at that creek with a survey sheet. We never call it
  one, in the README, in the video, or anywhere else.
- It is **not transferable between features**. A video labelled for its concrete banks says
  nothing about the plants on those banks, so those frames stay unlabelled for the plant feature.
- It is **not a claim about the water**. No frame carries a statement about pollution or health,
  and `/city` never states a risk for a named site.

What the search found, stated plainly: openly licensed creek footage whose description names a
feature is close to nonexistent. The Commons files that do (a storm drain in Accra, Himalayan
balsam in England) are under a minute long or CC BY-SA, which Update 14 excludes. So the footage
result leans on agreement between models, and the accuracy figure carries its count, which can be
zero. Adding footage with a supported label is the first thing to do with more time.

A frame's manifest row carries the source video, the second it was taken at, and the sentence
from the description (or the title) that supports its label, in `label_evidence`. If the row has no label, the
same field says the description supported none. Anyone can open the source video and check.

## Rules this list follows

- A synthetic or example thing is never counted in any number a person sees.
- A synthetic result is never cited without `--synthetic`, and never after data lock.
- An example resource in FHIR is tagged in `meta.tag` and says EXAMPLE in its narrative, so it
  stays an example even when copied out of this repository.
