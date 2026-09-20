# Rachel's pack (one page)

DRAFT, written 2026-09-20 by Claude Code for Alex to hand to Rachel. Plain words on purpose.

## What we need from you, and by when

| What | Wanted by | Latest without moving the launch |
|---|---|---|
| About 40 photos from the shot list below, originals kept, spot and date written down | Tue Sep 22, noon | Tue Sep 22, 19:00 |
| Your gold labels for the 16 test photos, done blind with the labelling tool | With the photos | Tue Sep 22, 21:00 |
| One rule of thumb per feature (12 words or fewer) with a source, and the four test questions in your words | Tue Sep 22, noon | Tue Sep 22, 21:00 (frozen at the tag) |
| The Bay Area invasive plant list, checked against the Cal-IPC Inventory | Tue Sep 22, noon | Tue Sep 22, 19:00 |
| Your approved health and ecology sentences, after reading the factsheets | Fri Sep 25 | Sat Sep 26, noon |
| One creek visitor on camera taking the test (with Alex), release signed | Sun Sep 27 | Mon Sep 28, 15:00 |

If a date slips, the launch slips a day for every day late. The data lock (Sun Sep 27, 18:00) does not move.

## The shot list

Phone, landscape, daylight, standing on the bank, both bank and water in frame. No people, house numbers or plates. Three shots per spot. Keep the originals. Write down the spot and the date. Use Strawberry Creek plus at least two other East Bay creeks, so lesson and test photos never share a spot. For each feature we need clear present, clear absent, and the look-alikes that fool people. Anything you would call ambiguous stays out of the test.

- Built banks. Present: concrete walls, stones set in concrete, a wall hidden under ivy. Absent: natural rock, a raw earth bank that looks messy.
- Dug-out channel. Present: straight reach, even sloped banks, the same width all along, flat slow water, no trees or trees all the same age. Absent: bends, bars, pools, fallen wood, changing width.
- Plants that do not belong. Present: showy single-species stands crowding the bank, checked against the regional list. Absent: native streamside trees and shrubs that look scruffy.
- Pipes and sewage signs. Present: a pipe running in dry weather, staining below an outlet, grey water. Absent: a dry pipe, a natural seep. For the running-pipe shots, note the date and that it had not rained for three days; a photo cannot show that on its own.
- Warm-up pair: one tidy, pretty, damaged creek and one messy, healthy one, as similar in size and light as you can find.

## How to label blind

1. Alex puts the photos into the repo with `scripts/ingest_photos.py`. You do not need to do that step.
2. In a terminal at the repo folder, run: `uv run python scripts/label_photos.py --name rachel`
3. A page opens in your browser. It shows one photo and one feature at a time. Pick present, absent, or ambiguous. Ambiguous means the photo leaves the test.
4. It writes `labels_rachel.csv`. It never shows you Alex's file, and his tool never shows him yours. That is what blind means here.
5. When both files exist, `scripts/merge_labels.py` lists every photo where you two disagree. You settle those together, then the key is frozen. You cannot change a label after that.

## How to edit the YAML files

The lesson text lives in plain text files under `content/drafts/lessons/`, one per feature: `artificial_bank.yaml`, `dug_out_channel.yaml`, `invasive_plant.yaml`, `pipe_running.yaml`. Open one in any text editor.

- Change only the words inside the quotes. Leave the names before the colons and the spacing alone.
- Limits the screen enforces: `rule_of_thumb` is 12 words or fewer; every caption and every feedback line is 25 words or fewer.
- Lines starting with `#` are notes to you. Delete them or leave them, they do not show anywhere.
- Do not type a long dash. Use a comma, a colon or a full stop instead. The build fails on a long dash.
- Check a file parses: `uv run python -c "import yaml; yaml.safe_load(open('content/drafts/lessons/pipe_running.yaml')); print('ok')"`
- Check for long dashes: `uv run python scripts/check_dashes.py`
- When you are happy with a file, change `approved: false` to `approved: true`. Alex copies it into `content/lessons/`. Until then it cannot reach a screen.

The same goes for `content/drafts/glossary.yaml` (one plain sentence per word), `content/drafts/regions/california-bay-area.yaml` (the plant list) and `content/drafts/approved_sentences.yaml` (the health card sentences).

## What to check in the drafts

- Is each cue true? Would a stream ecologist wince at any sentence? Cut or fix it.
- Do the captions match the shots you took? Each caption has a note saying which shot it expects. Swap or rewrite freely.
- The pipe lesson says "worth testing" and never "sewage" as a conclusion. Keep it that way.
- No sentence anywhere states a health risk for a specific creek. Nothing in the lessons is health advice.
- The plant list: strike anything you have not seen on an East Bay bank. Every plant left must have its Cal-IPC profile link. A species name goes on a screen only on a photo you have verified.
- The glossary: one plain sentence each, reading age about 12. Add any word from the form I missed.

Your health sentences wait for the factsheets. No sentence about health ships until you have read the OneAquaHealth Key Indicators Factsheets (DOI 10.5281/zenodo.20345207, free download) and flipped that sentence to `approved: true`. The candidates in `content/drafts/approved_sentences.yaml` are safe practice with a source; you may keep, change or delete any of them.
