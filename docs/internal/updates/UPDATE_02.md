# Second Look: mammoth prompt 2 (update to the master brief)

Paste this whole text into the Claude Code terminal. Everything below is addressed to Claude Code.

## 0. What to do with this

1. Finish the step you are on and commit it. Do not abandon Session A.
2. Save this text as `docs/updates/UPDATE_02.md`. Where it disagrees with `docs/MASTER_BRIEF.md`, this file wins.
3. Fold every item into PLAN.md under the session named in section 15, tagged MUST (before the Wednesday launch), SHOULD (before the Saturday freeze) or COULD (only if everything above it is green).
4. If an item costs more than it is worth before Sep 30, say so in your report and skip it. Deleting scope beats adding risk.
5. Then reply with the report block from section 1 and carry on.

## 1. How we work from now on

Alex works only in this terminal. He pastes your reports to the planner and pastes the planner's next prompt back to you. So a report has to make sense to someone who cannot see the repo.

End every session, and any moment you need a decision, with this block and nothing after it:

```
=== REPORT START ===
session: <letter and name>      commit: <short hash>      date: <UTC>
works now (command and the key line of its output, one per line):
failed or flaky (what, the error in one line, what you tried):
decisions you made (one line each, with the reason):
skipped from the brief or an update (item, why):
questions for the planner (3 at most, plain, no menus):
needed from humans (what, who, latest workable date):
next: <the first step of the next session>
=== REPORT END ===
```

Cost discipline, because Alex's usage limit is shared between this terminal and his chats:

- Keep replies short. Never print whole files into the terminal. Show the path and the few lines that matter.
- Run targeted tests while you work. Run the full `make check` once per milestone.
- After CLAUDE.md and PLAN.md exist, do not re-read the master brief in full. Read only the section a session names.
- Use subagents only when a task needs wide reading.

## 2. Amendments to the analysis plan

These must be in `docs/analysis_plan.md` before the `prereg-v1` tag. Nothing is tagged yet, so edit the plan directly and note the edit in the commit message.

1. Data lock in UTC. Add: "Data lock is 2026-09-28T01:00:00Z, which is Sunday Sep 27 at 18:00 PDT." The code uses one UTC constant. Add a test that a response stamped one second after lock is excluded and one second before is kept.
2. Source label. Add to the stored fields: "a coarse source label taken from the link (poster, chat, friends, creek_group, other)". Add to the descriptive outcomes: completed sessions by source. It is never used in the confirmatory test.
3. Hidden field. Add to the exclusions: "sessions that filled the hidden form field that people cannot see". Add the field to the consent form as a bot trap.
4. Demo. Add: "Sessions on the /demo route are never stored."
5. Backups. Add: "Automatic backups of the raw database are taken daily and kept private. Nobody computes outcomes from them. The only code that computes outcomes is the analysis script, which refuses to run before data lock."
6. What the score is for. Add this descriptive analysis, word for word:

> Consensus with and without scores (descriptive, no significance test). For group sizes 3, 5 and 7 we draw 2,000 random groups of completed sessions within each arm, without replacement inside a group, seed 20260920. For each test item the group's answer is decided two ways. Plain vote: Yes counts +1, No counts -1, Can't tell counts 0, and the sign of the sum is the answer. Scored vote: each person's vote is multiplied by a weight that comes only from the other three items of the same feature. With c of those three correct, p = (c + 0.5) / 4 and the weight is the larger of 0 and ln(p / (1 - p)). A person at or below coin-flip level on the other photos of that feature therefore gets no say and never a negative say. A sum of exactly zero counts as a wrong answer for both methods. We report, per arm and group size, the mean share of the 16 items the group gets right under each method, with the 2.5 and 97.5 percentiles over the draws. We publish it whatever it shows.

7. Examples are picked by rule, not by hand. Add: "The README shows the three test items with the largest gap between trained-arm accuracy and the best model's accuracy, in either direction, chosen by script."
8. People and models see different things. Add to the limits: "People see the photo at phone size. Models receive it resized to 1092 px on the long side."

## 3. The upgrade that shows what the score buys a city

`evals/consensus.py` implements amendment 6 exactly and writes `results/consensus_<date>.json` plus one plain chart: group size on the x axis, share of photos the group gets right on the y axis, four lines (untrained plain, untrained scored, trained plain, trained scored).

Test it on the synthetic sessions first. Build one synthetic case where people differ a lot in skill, in which the scored vote must beat the plain vote, and one where everyone is equally skilled, in which the two must tie within noise.

This is the payoff of the whole idea. Storing the score is only worth it if a city can use it. If five volunteers plus their scores get more photos right than five volunteers alone, that sentence goes on the first screen of the README. If they do not, the README says that instead.

In the analyst view add one toggle: "show only answers from people who passed this feature".

## 4. One viewer, two kinds of observer

OneAquaHealth says citizen data and lab data should stand side by side under the same profiles. Show it on one screen.

- From Session E on, read-only GET requests to their sandbox are allowed: one request per second, 50 per session at most, a user agent that names the repo. Still no writes beyond the tagged mirror, and never delete by search.
- Pick a few water chemistry Observations that they published there (Almyros is a stream site). Render one with exactly the same record component that renders our volunteer Observation from Strawberry Creek.
- The lab result shows its performer and method. The volunteer's answer shows the person's test score for that feature. Same profile, same viewer, two kinds of evidence.
- Cache what you fetch in our database, never in git. If the sandbox is down, the screen says so plainly and shows our own record alone.
- Add a "View as FHIR" toggle on every record: the JSON, a badge that says which guide commit it was validated against, and a curl line a judge can copy.

## 5. A proposal the standards people can use

Write `docs/ig_proposal.md`, one page, plain words: how their implementation guide could carry observer quality for citizen data. What we stored, where, why that shape, what the validator said, and the FSH example. Keep the FSH example building cleanly inside a copy of their guide at the pinned commit. Alex opens the pull request himself when the repo goes public. The page and the example are SHOULD. The pull request is COULD.

## 6. A log that cannot be quietly edited

About 50 lines, no new dependency. `audit/log.jsonl`, one JSON object per line: seq, ts_utc, kind, payload_sha256, prev_hash, hash. Kinds: plan_tagged, key_frozen, launch_wipe, model_pass_table, data_lock, record_written, sandbox_push. `scripts/verify_audit.py` walks the chain and fails on any break. The README prints the last hash at freeze and Alex posts it publicly. Call it an audit log. Never call it a blockchain.

## 7. Getting enough strangers

The number of completed sessions is the biggest risk in the project. Build the recruiting tools early.

- End screen share card: "I spotted 13 of 16. Two minutes. Can you beat me?" with a preview image made on the server from the score alone. No personal data. A forged score is harmless.
- A printable poster, made by the repo (HTML to PDF with Playwright): the two warm-up photos, the question "Which creek is healthier?", "Scan to find out. Two minutes. Anonymous." and a QR code that carries `?src=poster`. Letter and A4. No answer on the poster.
- Links carry `?src=` and the API stores only the coarse label from amendment 2.
- `GET /api/test/counts` also returns completed sessions by source, so Alex knows where to push. Counts only.
- The first screen must paint at once even if the API is asleep: make the landing page static and let it wake the API in the background.

## 8. Judge mode and a repeatable demo

- `/demo` gives feedback after each answer (it is not part of the test), ends with the features the judge missed, and shows only those lessons.
- `/demo?script=1` runs a fixed, seeded path with sample photos so the screen recording can be repeated shot for shot.
- The top of the README and the Devpost page both say: take the two-minute test yourself, no camera needed.

## 9. Spanish, checked by a person

The official app has a translation that seems to have drifted: its Italian pipes question appears to ask about rainwater where the English asks about polluted water. So we set a rule: no machine-only translation ever reaches our UI. Each locale file records who checked it and when. Ship an `es` locale only if Alex or another fluent person checks every string. COULD.

## 10. Offline at the creek

Creeks sit in gullies with poor signal. The guided check saves answers and downsized photos to a local queue and syncs when the phone is back online. Show a clear "saved on this phone, will send later" state. If the rainfall lookup or the location fails, skip the dry pipe question. Never guess. Let the person drop a pin or pick a saved spot when location permission is denied. SHOULD.

## 11. Roadblocks and their fixes

1. Photos arrive late or in the wrong shape. Build `scripts/ingest_photos.py` on Monday: a folder of originals (HEIC or JPEG) plus a labels CSV goes in; converted, EXIF-stripped, resized images and manifest rows come out. Hash after processing. Originals never enter the repo.
2. Two people must label without seeing each other's labels. Build `scripts/label_photos.py`: a local page that shows each photo and feature, writes `labels_<name>.csv`, and never shows the other file. `scripts/merge_labels.py` computes Cohen's kappa per feature, lists every disagreement for the two of them to settle, and refuses to freeze the key while any remain.
3. A sleeping host kills a demo. Pick a host whose API does not sleep, or add a scheduled ping every 10 minutes, and keep the static first paint from section 7. Put the measured time to first screen on a cold start in the report.
4. The FHIR toolchain breaks in CI. Pin the SUSHI version that built the spike cleanly (3.20.1), Node 20, Java 17 and one version of the HL7 validator jar. Cache `~/.fhir/packages`. Build their guide from the pinned commit. If the terminology server cannot be reached, rerun the validator with terminology checks off and write that fact into the results file. Never let a network hiccup turn CI red for a reason unrelated to our resources.
5. The sandbox write is still unproven. Alex runs `scripts/sandbox_write_test.sh`. A 201 means mirror as planned. A 401 or 403 means we show validated records in our own public read-only endpoint, the validator output, and the proposal from section 5. The story holds either way. Record the sandbox part of the video as soon as it works, because anyone can delete records there.
6. Losing responses mid-week. Daily automatic database backup, kept private, plus a restore drill once before launch.
7. Bots and repeat visitors. The hidden field from amendment 3. A short-lived in-memory rate limit per address that is never written to disk or logs. Say so in `docs/DATA_HANDLING.md`.
8. Uploads. Accept images only, check the file's real type, cap the size, downsize on the phone before sending, keep uploads in a private bucket, and delete after 30 days.
9. The Devpost form is unread. When Alex pastes its fields into `docs/notes/devpost_fields.md`, map each field to a README section in `docs/devpost.md`.
10. Compliance is scored by these organizers. Add `docs/SUBMISSION_CHECKLIST.md` and `make submit-check`: the track statement is the first line of the write-up; the five headers from the organizers' email exist; the video link is present and the video runs 3 to 5 minutes; a license file exists; the demo URL answers 200; a secrets scan is clean; verify_claims passes; the audit log verifies; the repo is public.
11. The clock. One UTC constant for data lock (amendment 1), stored times in UTC, shown in local time.
12. The track statement. Save this as `docs/track_statement.md` and keep it true: "Track 3, AI-Supported Assessment. The track says citizen observations can be inconsistent and error-prone. We measure that, per person and per feature, with a two-minute photo test, and we save the result with every observation. AI takes the same test. It may only raise a question on features where it passed, and the volunteer always answers first."

## 12. Data access, settled

- Nobody outside the consortium has citizen answers or photos. Their public citizen endpoint returns only a name, coordinates, altitude and a site code. That is why every photo here is ours or openly licensed.
- Their scientists' data platform is closed to us. We do not need it.
- The Resilience Map API stays off limits until Alex says permission arrived. It would feed only a context line. The project does not depend on it.
- If we ever need their published pilot numbers, the guide's public GitHub repo has them. The same rule applies: fetch script, dated manifest, derived numbers only.
- Other teams are asking in the forum where the data is and getting only a Slack link. Alex will check the Slack for an official data set and for the two missing workshop recordings, and put what he finds in `docs/notes/slack.md`.

## 13. Video beats, for the script in Session G

Target 3:45. Write `docs/video_script.md` with one line of speech and one shot per beat, tied to real screens.

- 0:00 Two creek photos. "Which one is healthier?" Five seconds of quiet. Then the answer.
- 0:20 The project lead's point in one line. Professional surveyors must pass a test before their data counts. Volunteers never have.
- 0:40 A real person at Strawberry Creek takes the two-minute lesson on a phone.
- 1:30 The table: untrained people, trained people and each model on the same 16 photos, with the number of people, and the plan that was published before anyone took it.
- 2:10 At the creek: the guided check, and the question "It has not rained here for N days. Is anything coming out of that pipe?"
- 2:40 The record: an answer beside "4 of 4 on built banks". View as FHIR. Validated. The same viewer shows a lab result from their own sandbox.
- 3:10 What the score buys a city: five volunteers with scores beside five volunteers alone.
- 3:30 Berkeley as a follower city in their five steps. Any city can do this. Take the test yourself.

## 14. Human tasks, updated

Today, while you build:

- Alex goes to Strawberry Creek with the shot list from section 16 of the master brief. One trip, three jobs: lesson and test photos, video footage, and one assessment in the official app with a screenshot of every screen.
- Alex joins the hackathon Slack and saves the channel list and pinned posts to `docs/notes/slack.md`.
- Alex runs `scripts/sandbox_write_test.sh` with the repo URL filled in and saves the output to `docs/notes/sandbox_write_test.txt`.
- Alex pastes the Devpost form fields into `docs/notes/devpost_fields.md`.
- Alex watches OneAquaHealth's ten-minute AI image model video and writes five lines in `docs/notes/their_image_model.md`: what it classifies, on which photos, whether it is live in the app.
- Alex sets the API workspace spend limits and alerts from the budget.

By Tuesday noon: Rachel's photos and blind labels, her rule of thumb for each feature with a source, and the Bay Area plant list.

From Wednesday: recruiting. Lab and class chats, club servers, friends and family, posters near campus bridges where posting is allowed, and local creek groups (for example Friends of Five Creeks, and the campus office that looks after Strawberry Creek; Alex checks names and contacts himself). One creek visitor on camera taking the test, with a signed release. Write a one-page plain release form at `docs/release_form.md`. It is a template, not legal advice.

## 15. Updated session map

- Session A (running): unchanged, plus the UTC lock test.
- Session A2 (next, short): section 2 amendments, `evals/consensus.py` with its two synthetic cases, `scripts/ingest_photos.py`, `scripts/label_photos.py`, `scripts/merge_labels.py`, the audit log and its verifier. MUST.
- Session B: add the share card, the poster, source labels, the static first paint, judge mode feedback. MUST except the poster's A4 size.
- Session C: ingest the real photos, merge labels, settle disagreements, freeze the key, the restore drill, preflight (now also checks the audit log, the hidden field and the UTC lock), tag, real model run. MUST.
- Session D: add the offline queue and the fail-closed rules for rainfall and location. SHOULD.
- Session E: add the two-observer viewer, View as FHIR, the proposal page, the sandbox fallback. SHOULD.
- Session F: add the rule-picked examples, the seeded demo path, the video script. SHOULD.
- Session G: add the consensus chart, `make submit-check`, the Devpost mapping. MUST.
- COULD, in this order: the Spanish locale, the small read-only MCP server over our own records (get a creek's record, list visits, get an observer's score), the downstream note, the pull request.

## 16. Reply now

Send the report block. In "works now" say where Session A stands. In "skipped" name anything here you would drop and why. In "questions" ask only what blocks you.
