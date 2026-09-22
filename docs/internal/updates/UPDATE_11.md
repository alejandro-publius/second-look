# Second Look: mammoth prompt 11 (content in, freeze, tag, launch)

Paste this once the photo picks are saved as `photos/candidates/picks-*.csv`. Start a fresh window with `cd ~/second-look && claude`, then paste this whole text. Everything below is addressed to Claude Code.

Read `CLAUDE.md`, `PLAN.md` and `docs/HANDOFF_NEXT.md` first. Save this text as `docs/updates/UPDATE_11.md`. Work on `main`, the launch build. Do not touch the `depth` branch. Alex is at the keyboard for this session and answers in a word or two, so ask him only what the steps below name, one thing at a time, and carry on the moment he answers.

## 1. A preflight for the launch only

Split preflight in two. `make preflight-launch` gates only what the two-minute test uses: the warm-up pair, the lesson and practice photos with their marks and copy, the 16 test photos with labels, the four question wordings, the consent text and contact email, backups, the tag. `make preflight-judges` keeps everything else (the creek check form, approved health sentences, the sample record) and does not block Wednesday. Show Alex both counts.

## 2. Photos in

1. Run the batch fetch over the picks files. Ingest, write the manifest rows with author, licence, source and label evidence, and run the loader checks.
2. Print one table: feature by role, picked against target, and every refusal with its reason (scene clash, licence, size, laid stone in the test role). If a slot is short, name the contact sheet to reopen and stop until Alex types `picks updated`.
3. Build the lesson files from the lesson photos: two contrast pairs and one practice photo per feature, plus the warm-up pair. The credits page lists every author and licence.

## 3. Words

Show Alex, in one screen each, and take `ok` or his edit:

1. The four test questions. The official app's own wording for built banks, invasive plants and pipes, and ours for the dug-out channel. Save the app strings the planner pulled on Sep 20 to `docs/notes/app_strings.md` and mark those three items verified against the app's public text, with that date.
2. The four rules of thumb, 12 words or fewer, each with its source.
3. The lesson captions and practice feedback from the drafts.
4. The consent text, with his contact email filled in.

Stamp each approval with his name and the date. Write the frozen question wording into `docs/analysis_plan.md`.

## 4. Marks

Start the marking page and give Alex the local link. He clicks each lesson photo, places the marks, types labels of five words or fewer, and approves photo by photo. Wait until he types `marks done`. Then run the mark checks.

## 5. Labels and the key

1. The label chosen at picking is the first gold label. If a second person has labelled through `scripts/label_photos.py`, merge, print Cohen's kappa per feature and list the disagreements for Alex to settle. If not, write "one labeller" into the plan and the README's Known weaknesses and move on.
2. Record kill tests K3 and K4 by their written lines.
3. Run `scripts/freeze_key.py`. It writes the key hash and the first audit log entry.

## 6. Backups

Check the two GitHub secrets. If they exist, turn the schedule on, run one backup, and do the restore drill. If they do not, print the two commands Alex has to run, continue with the other steps, and leave the launch blocked on this one line.

## 7. Dry run

Deploy `main` with the `is_test` key. Give Alex one link to send to three friends on their own phones. When he types `dry run done`, show him what they struggled with from the timings and any unsent counts, fix only what would confuse a stranger, wipe the test sessions, and log the wipe in `docs/deviations.md`. Record K2, K1 and K8 if he gives you their results.

## 8. Tag and launch

1. Run `make preflight-launch`. It must print 0 failed.
2. When Alex types `freeze`, commit, tag `prereg-v1`, push the tag, add the audit entry, and print the SHA-256 of `docs/analysis_plan.md` for him to post publicly.
3. Deploy. Confirm the counts endpoint shows zero sessions, `/demo` shows "Judge mode opens on Sep 28", and the landing page paints in under 3 seconds cold.
4. Print the public link, the poster PDF paths, and the three recruiting messages from `docs/recruiting_messages.md` with the link and the right `?src=` filled in.

## 9. Report

Write the report file, copy it to the clipboard with `pbcopy`, and print the report block: the two preflight counts, the photo table, kappa or "one labeller", the plan hash, the live link, and anything that would stop a stranger finishing the test.
