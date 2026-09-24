# Data card: the photo set and the footage set

What the photos and the creek footage are, where they came from, under which licence, who
labelled them and how, and what carries no label at all. Every number here is read from a file
in `results/` and checked by `make verify-claims`. The counts come from the manifests through
`evals/data_card.py`, which writes `results/data_card.json`; a test fails when that file is not
what the manifests say (`evals/tests/test_data_card.py::test_the_committed_file_is_what_the_manifests_say`).

## The sets

| Set | What it is for | Rows | Where |
|---|---|---|---|
| Test photos | the 16 items of the two-minute test, 4 per feature, and the 16 photos every model is tested on | <!--v:results/data_card.json#/photos/test/rows-->16<!--/v--> | `photos/manifest.csv`, role `test` |
| Lesson photos | the lesson cards, with their numbered marks | <!--v:results/data_card.json#/photos/lesson/rows-->16<!--/v--> | role `lesson` |
| Practice photos | one worked example per feature | <!--v:results/data_card.json#/photos/practice/rows-->4<!--/v--> | role `practice` |
| Warm-up photos | the "Which creek is healthier?" pair on the first screen | <!--v:results/data_card.json#/photos/warmup/rows-->2<!--/v--> | role `warmup` |
| Footage frames | stills cut from open creek videos, for the model run on footage | <!--v:results/data_card.json#/photos/benchmark/rows-->46<!--/v--> | role `benchmark`, `results/footage_pool.json` |
| Footage videos | the videos those frames and the walks come from | <!--v:results/data_card.json#/videos/rows-->5<!--/v--> | `videos/manifest.csv` |
| Film footage | the clips and photos in the demo film | <!--v:results/data_card.json#/film_footage/rows-->13<!--/v--> | `docs/video/footage.csv` |

In all, `photos/manifest.csv` has <!--v:results/data_card.json#/photos/rows-->84<!--/v--> rows, one per
image, and `make manifest-check` fails when an image under `photos/` has no row or its hash does
not match. The smaller AVIF and WebP copies of the two warm-up photos have their own rows in
`photos/derived/manifest.csv`. No media file from the footage set is committed: videos stay in a
cache outside the repository.

## Sources

**Photos.** By the host of each row's source page: Wikimedia Commons
<!--v:results/data_card.json#/photos/by_source/Wikimedia Commons-->35<!--/v-->, iNaturalist
<!--v:results/data_card.json#/photos/by_source/iNaturalist-->9<!--/v-->, and frames from YouTube videos
<!--v:results/data_card.json#/photos/by_source/YouTube-->40<!--/v-->. The test photos come from Wikimedia
Commons (<!--v:results/data_card.json#/photos/test/by_source/Wikimedia Commons-->12<!--/v-->) and
iNaturalist (<!--v:results/data_card.json#/photos/test/by_source/iNaturalist-->4<!--/v-->).

- `scripts/find_open_photos.py` searched both collections, one request a second, and wrote a
  contact sheet a person reads. Plants came from research grade iNaturalist observations,
  California first.
- `scripts/fetch_open_photo.py` and `scripts/batch_fetch_photos.py` fetched each chosen photo
  with its author, licence and the source's own words, and handed it to
  `scripts/ingest_photos.py`: resized, EXIF, ICC and comments cut out, hashed after processing
  (`scripts/tests/test_ingest_photos.py::test_ingest_strips_exif_resizes_and_writes_rows`).
- The photos come from several countries and seasons, not from the creeks in Berkeley. Only the
  iNaturalist rows carry a capture date and a coarse place.

**Footage.** `scripts/find_open_videos.py` searched Wikimedia Commons and YouTube for footage
under CC BY, CC0 or public domain, and found <!--v:results/footage_pool.json#/candidates-->68<!--/v-->
candidates.
`scripts/pick_videos.py` picked by written rule (licence, length, height, a creek named in the
title or description), and `scripts/make_frames.py` screened sampled frames on the Mac with
Apple's Vision framework and OpenCV for people, faces, text, plates and frames with no water.
In the last cut it dropped <!--v:results/footage_pool.json#/frames_dropped_in_last_cut/person-->154<!--/v-->
frames for a person, <!--v:results/footage_pool.json#/frames_dropped_in_last_cut/text on screen-->75<!--/v-->
for text on screen and <!--v:results/footage_pool.json#/frames_dropped_in_last_cut/no water-->284<!--/v-->
with no water in view. <!--v:results/footage_pool.json#/videos_failed-->59<!--/v--> videos failed, most
because too few frames passed the screen. A person looked at every kept frame before it was
committed. What is left: <!--v:results/footage_pool.json#/frames_kept-->46<!--/v--> frames from
<!--v:results/footage_pool.json#/videos_kept-->5<!--/v--> videos in
<!--v:results/footage_pool.json#/countries_kept-->3<!--/v--> countries.

**Film footage.** The planner's list in `docs/video/footage.csv`, all from Wikimedia Commons
(<!--v:results/data_card.json#/film_footage/by_source/Wikimedia Commons-->13<!--/v--> rows), fetched by
`scripts/fetch_footage.py`, which asks Commons for each licence again and drops a file whose
licence changed (`scripts/tests/test_fetch_footage.py::test_a_changed_licence_downloads_nothing`).

## Licences

Every photo row names its licence at the exact version, and `make manifest-check` refuses one
that is not on the allow list in `core/content_loader.py`
(`core/tests/test_harden_content_loader.py::test_a_licence_off_the_allowlist_is_refused`).
Every author is credited on `/credits` and in the manifest.

| Licence | Photo rows |
|---|---|
| CC BY 2.0 | <!--v:results/data_card.json#/photos/by_licence/CC-BY-2.0-->1<!--/v--> |
| CC BY 3.0 | <!--v:results/data_card.json#/photos/by_licence/CC-BY-3.0-->47<!--/v--> |
| CC BY 4.0 | <!--v:results/data_card.json#/photos/by_licence/CC-BY-4.0-->7<!--/v--> |
| CC BY-SA 2.0 | <!--v:results/data_card.json#/photos/by_licence/CC-BY-SA-2.0-->15<!--/v--> |
| CC BY-SA 3.0 | <!--v:results/data_card.json#/photos/by_licence/CC-BY-SA-3.0-->5<!--/v--> |
| CC BY-SA 4.0 | <!--v:results/data_card.json#/photos/by_licence/CC-BY-SA-4.0-->6<!--/v--> |
| CC0 1.0 | <!--v:results/data_card.json#/photos/by_licence/CC0-1.0-->2<!--/v--> |
| Public domain | <!--v:results/data_card.json#/photos/by_licence/public-domain-->1<!--/v--> |

- All <!--v:results/data_card.json#/photos/benchmark/rows-->46<!--/v--> footage frames are CC BY 3.0: the
  one Commons video says so, and the <!--v:results/data_card.json#/videos/by_source/YouTube-->4<!--/v-->
  YouTube videos carry YouTube's "Creative Commons Attribution license (reuse allowed)", which
  is CC BY 3.0.
- The film footage keeps its own licences, listed in `docs/video/CREDITS.md`. Because some of it
  is CC BY-SA, the film is released under CC BY-SA 4.0.
- None of these photos is ours. A photo of our own would be CC BY 4.0, and there is none yet.
- No row is marked synthetic (<!--v:results/data_card.json#/photos/marked_synthetic-->0<!--/v-->) and no
  row is marked as showing a face (<!--v:results/data_card.json#/photos/marked_with_faces-->0<!--/v-->).
  Ingest refuses either (`scripts/tests/test_ingest_photos.py::test_refuses_synthetic_or_faces_and_writes_nothing`).

## Labelling method

**The features.** Four: built banks, a dug-out channel, plants that do not belong, and a pipe
running into the creek. Each has one written question, frozen before the test opened, in
`content/features.yaml`. A plant is "present" only for a species on the Cal-IPC Inventory for
the Bay Area (`content/regions/california-bay-area.yaml`), and the evidence must link the Cal-IPC
page. Laid stone is kept out of the test set, because the official app, the River Habitat Survey
and our form would each file it differently; `make manifest-check` fails on a test photo whose
source names it.

**Who labelled.** One labeller. The second label column is filled on
<!--v:results/data_card.json#/photos/with_second_label-->0<!--/v--> rows, so no agreement figure exists, and `results/key_hash.json` records <!--v:results/key_hash.json#/labellers-->1<!--/v-->
labeller. What the record in git shows about how the labels were set:

- A photo's gold label is the label chosen when it was picked.
- The picks, and the label column in them, came from the planner's picks file. The planner is
  a Claude chat that Alex plans with. That file lives in a folder under `photos/` that git
  ignores, so it is not in the repository; the commit that brought the photos in, 81e62ed, says the labels came from it.
- The analysis plan says a team member set the key, blind to any model output, and the README
  names Alex Velazquez. No blind label file by him exists yet. The fix is ready:
  `uv run python scripts/label_photos.py --name alex --roles test` labels the 16 test photos without showing the key, and
  `scripts/merge_labels.py` compares the two files and reports Cohen's kappa per feature.

**The evidence.** Every row carries `label_evidence`
(<!--v:results/data_card.json#/photos/with_label_evidence-->84<!--/v--> of
<!--v:results/data_card.json#/photos/rows-->84<!--/v-->): the source page's own words that back the label.
For example, the first built bank photo's Commons page says "This part of the creek is encased in
a concrete channel." A frame's evidence is the video's description, and says when that
description supports no label.

**The key.** `scripts/freeze_key.py` hashed the 16 test labels into `results/key_hash.json` and
wrote the moment to the audit log. The key never ships to a browser: the web build fails if a
served file carries a gold label (`apps/web/scripts/check-bundle.mjs`).

## What is labelled and what is not

| Set | Labelled | What the label is |
|---|---|---|
| Test photos | <!--v:results/data_card.json#/photos/test/labelled-->16<!--/v--> of <!--v:results/data_card.json#/photos/test/rows-->16<!--/v--> | <!--v:results/data_card.json#/photos/test/present-->8<!--/v--> present and <!--v:results/data_card.json#/photos/test/absent-->8<!--/v--> absent, 2 and 2 for each feature; the key the test and the models are scored against |
| Lesson photos | <!--v:results/data_card.json#/photos/lesson/labelled-->16<!--/v--> of <!--v:results/data_card.json#/photos/lesson/rows-->16<!--/v--> | <!--v:results/data_card.json#/photos/lesson/present-->8<!--/v--> present and <!--v:results/data_card.json#/photos/lesson/absent-->8<!--/v--> absent; used to teach, never scored |
| Practice photos | <!--v:results/data_card.json#/photos/practice/labelled-->4<!--/v--> of <!--v:results/data_card.json#/photos/practice/rows-->4<!--/v--> | all present; never scored |
| Warm-up photos | <!--v:results/data_card.json#/photos/warmup/labelled-->0<!--/v--> of <!--v:results/data_card.json#/photos/warmup/rows-->2<!--/v--> | no feature label; which creek is healthier is a judgement the end screen explains, and the warm-up answers are described, never scored |
| Footage frames | <!--v:results/data_card.json#/photos/benchmark/labelled-->0<!--/v--> of <!--v:results/data_card.json#/photos/benchmark/rows-->46<!--/v--> | none: no video's description named a feature clearly enough, so the footage run reports agreement between models, not accuracy |
| Footage videos | <!--v:results/data_card.json#/videos/labelled-->0<!--/v--> of <!--v:results/data_card.json#/videos/rows-->5<!--/v--> | none |
| Film footage | not labelled | used only in the film |

## Known gaps

- One labeller, and the record cannot yet show that the key was set blind. Until a second, blind
  label file exists, read every accuracy figure as agreement with this key.
- Four test photos per feature is a small set. It shows a person what to practise; it cannot rank
  people finely.
- The photos are from other countries and seasons than the creeks a Berkeley volunteer will see.
- No footage frame has a label, so nothing measures a model's accuracy on footage.

## Check it yourself

- `uv run python evals/data_card.py --check`: the counts above against the manifests.
- `make manifest-check`: every image has a row, a hash that matches, an allowed licence, no face
  and no synthetic flag.
- `uv run pytest -q evals/tests/test_data_card.py scripts/tests/test_ingest_photos.py`.
