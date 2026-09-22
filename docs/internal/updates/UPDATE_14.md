# Second Look: mammoth prompt 14 (everything that can run without Alex)

Alex, before pasting: close the launch window (the one in ~/second-look). Then in the bottom tab run this one line with your real key, and open a fresh window with `cd ~/second-look-depth && claude`:

```
grep -q ANTHROPIC_API_KEY ~/second-look-depth/.env 2>/dev/null || echo 'ANTHROPIC_API_KEY=PASTE_KEY_HERE' >> ~/second-look-depth/.env
```

Everything below is addressed to Claude Code.

## 0. This run

You own both worktrees for this run: `~/second-look` (branch `main`, the live launch build) and `~/second-look-depth` (branch `depth`). The other Claude Code window is closed. Read `CLAUDE.md`, `PLAN.md` and `docs/HANDOFF_NEXT.md` in both worktrees first. Save this text as `docs/updates/UPDATE_14.md` on depth. Where it disagrees with earlier files, this one wins. Every hard rule stands except where a section below says otherwise.

Facts that change earlier plans:

- Alex has dropped the recruited study. Nobody is being recruited. The two-minute test stays live as the volunteer's calibration step and for judges, and any sessions that arrive are reported as a description with their count. Nothing depends on them. The freeze on production during the study is lifted, on one condition: after every deploy the phone end-to-end tests pass against production.
- The evidence for the project is now the full loop and the AI on real creek footage from around the world, plus the AI on the same 16-photo test.
- Do not ask the planner questions. Decide, write the decision and the reason in `docs/DECISIONS.md`, and keep going. The planner reads the report at the end.

How to work:

- Phases in order. After each phase: `make check` green, commit, push, refresh `docs/HANDOFF_NEXT.md`, five lines in `docs/internal/BUILD_LOG.md` (create the folder in phase 2). If your context gets tight, write the handoff and continue in a fresh subagent. If billing stops you, the handoff is current.
- Subagents, two at a time at most, only for work that is independent and fully specified, with a brief of 20 lines or fewer each and the list of files it may touch.
- Paid model calls only through the Batch API where possible, logged to `results/cost_log.jsonl`, capped at 40 dollars for this whole run. If `ANTHROPIC_API_KEY` is missing from `~/second-look-depth/.env`, build every AI step against the fake client, keep the README's result slots as "results arrive with the model run", and end the report with the one command Alex must run.
- You may install developer tools (ffmpeg, yt-dlp, Playwright browsers, ImageMagick) with Homebrew, npm, uv or pipx.
- Never: make the repo public, delete by search or `$expunge` on the sandbox, call `api.enora-oah.eu`, store a real participant from a test route, put an em dash, en dash or emoji anywhere, commit a secret or a video file, show a person an image without a manifest row, state a risk for a specific site, or copy code from Alex's earlier projects.

## 1. Launch on main

In `~/second-look`, on `main`:

1. Add this line to `docs/analysis_plan.md` section 7 before tagging: "Recruitment is not planned. Sessions that arrive through the public link are reported as a description with their count, and nothing in this project depends on them." Add to section 3 that the key was set by one labeller if that is not already there.
2. Run `make preflight-launch`. It must print 0 failed apart from the tag itself. If anything else is red, fix it if it is code, and otherwise list it in the report and continue with the rest of this prompt.
3. The dry run: the deployed smoke tests pass on both arms against the live deployment, and Alex has taken the test himself. Log in `docs/deviations.md` that no separate dry run with friends was held, with the date.
4. Run `scripts/wipe_for_launch.py`. Log the wipe in `docs/deviations.md`.
5. Commit, tag `prereg-v1`, push the tag, add the audit entry, write the SHA-256 of `docs/analysis_plan.md` to `docs/notes/plan_hash.md`.
6. Deploy `main`. Confirm the counts endpoint shows zero sessions, `/demo` shows "Judge mode opens on Sep 28", the landing page paints in under 3 seconds cold, and the phone end-to-end tests pass against production. Record the public link in `docs/notes/hosting.md`.

## 2. Content and cleanup (on depth)

1. Approved sentences. Copy these ten from `content/drafts/approved_sentences.yaml` into `content/approved_sentences.yaml` with `approved: true`, `approved_by: "Alex Velazquez"`, today's date, and a note that the planner checked each against its source text on 2026-09-21: city_replant_margins, city_fix_sewers, city_reconnect_floodplain, city_remove_barriers, city_remove_concrete, pet_keep_out_foam, pet_rinse_after, pet_bring_water, pet_call_vet, person_avoid_foam_scum. For person_rinse_hands, person_no_swallow, person_avoid_pipes and person_report_dry_pipe, fetch the cited page or PDF again, put the matching sentence in a `source_quote` field, and approve only where you find it. Prove with a test and a screenshot that `/city` shows what the creek needs and the health card shows one action each for the person, the pet and the city.
2. Say where the city actions come from, on `/city` and in the README: OneAquaHealth's own restoration measures, from the OneAquaHealth Policy Brief (2026), page 9, with the link.
3. In `docs/ig_proposal.md`, under what we found, one friendly line: their temporary code system spells one code "morophology"; we kept their spelling so our records validate; they may want to correct it before it spreads.
4. Hosting is Cloudflare only. Delete `fly.toml`. Remove Vercel and Fly from `scripts/deploy.sh`, `docs/THIRD_PARTY.md`, `docs/CONTRACTS.md`, `docs/notes/hosting.md` and every other live file. Leave history and old reports alone.
5. Planning notes out of the product docs. `git mv` into `docs/internal/`: `MASTER_BRIEF.md`, `updates/`, `reports/`, `reviews/`, `KILL_TESTS.md`, `CONTEXT_LEDGER.md`, `alex_today.md`, `team_pack.md`, `recruiting_messages.md`, `BUILD_LOG.md`, `DEPTH_MAP.md`. Add `docs/internal/README.md`: "Working notes between the team and their AI coding tools. Not part of the product." Fix every path that pointed at them. In `DEPTH_MAP.md` rename the judge column to "who it serves". `CLAUDE.md`, `PLAN.md` and `docs/HANDOFF_NEXT.md` stay where sessions expect them. From now on, new reports and updates go under `docs/internal/`.
6. Remove any README or plan wording that promises a result from recruited participants.

## 3. AI on the test and on real creek footage (on depth)

1. The 16-photo test. Run the three configured models on the 16 test items with the frozen question wording, three runs each, Batch API, and write the pass table, per-feature accuracy with Wilson intervals, the notes they gave, and cost to `results/`. Confirm the three model ids against the current models page first and record ids, prices and the date in `docs/notes/model_ids.md`.
2. Find footage. `scripts/find_open_videos.py` searches Wikimedia Commons video files and YouTube through yt-dlp metadata search (no download yet), keeping only Creative Commons Attribution, CC0 and public domain, 1 to 20 minutes, 720p or better, where the title or description says it is a creek, stream or urban river walk. Write `videos/candidates.html` and `videos/candidates.json` with title, author, licence, duration, country if stated, and link. Aim for 40 candidates across as many countries as you can find: concrete channels, restored creeks, natural streams, outfalls.
3. Pick by rule, not by taste: licence allowed, footage mostly of the water and banks, spread across countries and across our four features. Choose 12. Write `videos/manifest.csv` with licence, attribution, link and the description text that supports each label. Download to a cache outside the repo. Never commit a video file.
4. Frames. Sample one frame every few seconds, drop near-duplicates with a perceptual hash, drop any frame with a person or a readable plate or house number using a local detector, keep at most 15 per video, about 150 in all. Commit the frames we display, resized, with a manifest row each (role `benchmark`, source video, timestamp) and the author on the credits page.
5. Labels, stated honestly. A frame's label comes from the video's own description where it supports one (a concrete flood channel is a built bank), otherwise the frame is "unlabelled" and is used only for agreement between models. Write exactly this method into `docs/REAL_VS_SYNTHETIC.md`. Never call it a gold standard.
6. The AI on the footage. Run the three models on the frame pool, Batch API, three runs, capped at 25 dollars of the 40. Report per feature: accuracy against description labels with intervals, agreement between models on unlabelled frames, how many flags the gate dropped and why, and the adversarial frames. Run the ablation (rules only, context only, vision only, all three) on the labelled frames.
7. The video walk. `/walk/<id>` plays a short clip, 30 to 45 seconds and under 20 MB, cut from a Creative Commons video, served from our own origin with its credit on screen. The person does the guided creek check while watching. The checker's flags for that clip are computed at build time, pass through the gate, and at most one becomes a question, shown only after the person has answered. The visit becomes a validated FHIR record tagged as a demo, feeds `/city` as a demo creek, and is never mirrored or counted. Ship four walks from four countries. Link them from `/judges` as "Check a creek from your desk".
8. The numbers for the README, all through `results/` and verify_claims: creeks and countries run through the full loop, frames judged, per-feature results, gate drops, records validated with 0 errors, cost per 100 frames.

## 4. The README and docs in the winning shape (on depth)

Run tier 3 of `docs/internal/updates/UPDATE_10.md` section 3 in full: the blockquote and badges, real screenshots, the "See it work" table, the trust tables ("Why trust a volunteer, and the AI?" and "What the AI cannot do"), the three Mermaid diagrams with `make diagrams` in CI, the "How OneAquaHealth is used" table, "Contributed back", "Evals", "What is real and what is synthetic", "For judges" with `make judge-check`, `docs/JUDGE_SCORECARD.md`, `docs/ACCEPTANCE.md`, `docs/ARCHITECTURE.md`, the repo map and the licence.

Specifics for this run:

- The first screen: the one sentence, the two real warm-up photos, the live link, and one table of the AI on the same 16 photos with the footage numbers beside it. Human arms appear only if sessions exist, with the count. No synthetic number anywhere in the README. If the key was missing, the slots say "results arrive with the model run".
- The "See it work" table uses the golden Strawberry Creek visit that already exists on depth. When Alex's real creek visit arrives, a later session swaps it in.
- Line one of the README stays the track statement from `docs/track_statement.md`.
- "How this was built" says plainly what AI coding tools did and what the two humans did.
- Known weaknesses, in full: one labeller; four photos per feature is coarse; photos from open collections in several countries and seasons; the footage labels come from descriptions; the citizen observer is modelled as a Practitioner; judge mode shut until Sep 28; no recruited study.
- Every number verified by `scripts/verify_claims.py`. `make judge-check` runs with no key and no network.

## 5. How it feels (on depth)

Run stage 2 of `docs/internal/updates/UPDATE_06.md` section 3 on `/check`, `/spot`, `/two`, `/quick`, `/city`, `/judges`, `/walk` and `/poster`, with the same tokens and components as stage 1. Playwright screenshots of every screen at 390 by 844 into `docs/screens/`, plus desktop for `/`, `/city`, `/two` and `/judges`. One critic subagent that wrote none of the UI looks at no more than 12 screenshots and writes `docs/internal/reviews/DESIGN_REVIEW_02.md`; fix the top findings. Draft the `es` locale and mark it unverified; it stays out of the build until Alex signs it. Add `make readability` to `make check` with a short exceptions list.

## 6. Merge and deploy

1. Merge `depth` into `main` in the order written in `docs/notes/hosting.md`: apply the additive D1 tables and deploy the Worker, run the study contract tests and the phone end-to-end tests against production, then ship the Pages file that puts the API behind the same origin, then run the phone tests again. Prove with `git diff --stat prereg-v1..HEAD -- apps/web/app/t apps/web/app/consent apps/api/study.py worker/src/study.ts` (adjust the paths to the real ones) that the test flow and the study endpoints are untouched by the merge. If they are touched, stop the merge and report.
2. Close draft pull request #1 as merged. `main` and `depth` are the same commit afterwards; keep working on `depth` and merging forward.
3. Sandbox mirror. Confirm the golden visit and the Library entry are still on their sandbox; re-push if not. Install a launchd job that runs `scripts/repush_sandbox.py` at 08:00 on Sep 28, Sep 30 and Oct 1 and logs to `~/second-look-backups/repush.log`, because anyone can delete records there. Real creek visits are mirrored once, as one tagged batch, after Alex's Strawberry Creek visit arrives; two-minute test sessions are never mirrored.

## 7. The video, as far as software can take it

Alex records his own voice and the creek footage. Everything else is produced here.

1. `docs/video/SHOTLIST.md` from `docs/video_script.md` and the beats in `docs/internal/updates/UPDATE_02.md` section 13, updated to the real screens and the footage results, target 3:45. One row per beat: time, clip file, duration, what is on screen, the line Alex says, and whether the beat needs creek footage or a person on camera.
2. Screen recordings with Playwright's video recording, phone viewport at the highest size Playwright allows, 30 frames a second, at a human pace with pauses between taps: the landing pair and the guess, consent, one lesson card with marks, three test items, the end screen with the gauges, judge mode (recorded against a local build with the lock constant overridden in the test environment only), the creek check with the dry pipe follow-up, the record with View as FHIR and the validation badge, `/two`, `/city`, one `/walk`, and a desktop capture of the README first screen and the sandbox Library entry. Save to `docs/video/clips/` as mp4 through ffmpeg. Clips are committed only if under 15 MB each; otherwise list their paths and keep them outside the repo.
3. `make video-rough` assembles `docs/video/rough_cut.mp4` with ffmpeg: 3-second title cards between beats, the script line burned in as a caption, a grey card wherever creek footage or a person on camera goes, and a scratch voice track from macOS `say` so the timing can be checked. Label the scratch track in the file name and in SHOTLIST.md. Alex replaces it with his own voice.
4. Write `docs/video/RECORD_AT_THE_CREEK.md`: the exact shots to get at Strawberry Creek in 30 minutes, with durations, plus the release form path for anyone on camera.

## 8. Submission pack

1. `docs/devpost.md` with every field ready to paste: project name, a tagline under 200 characters, the track statement as the first line of the description, the description under the organizers' five headers (the problem; alignment with OneAquaHealth; innovation and practical value; effective use of data, technology, AI, APIs and standards; a clear demonstration), the users and the impact on ecosystem and human health, "Built with", the live link, the `/judges` link, the repo link, a slot for the video link, and five gallery images chosen from `docs/screens/`. Plain words, no hype, every number matching the README.
2. `make go-public`, prepared but not run: `git rm -r docs/internal`, remove any reference to it, run `make submit-check`, and only then `gh repo edit --visibility public`. Print what it would do. Alex runs it on Sep 30.
3. Run `make submit-check` now. It must fail only on: the video link, the repo being public. Anything else red gets fixed.
4. `docs/ALEX_TODO.md`, one page, in order with dates: the creek visit and what to shoot, the voice recording against the rough cut, the Devpost fields and inviting Rachel to the draft, the video upload, `make go-public`, the dry-run submission on Sep 28, submit by 6pm Sep 30. Nothing on that page may be something software could have done.

## 9. Report

Write the full report to `docs/internal/reports/<UTC timestamp>.md`: the report block from UPDATE_02 with the gates line, then for each phase what shipped, its proving command and key line, and what was cut and why; the AI numbers; the merge diff proof; the `make judge-check` and `make submit-check` output; the rough cut's length and the beats that still need footage; the five things you think a judge would still find thin. Copy the file to the clipboard with `pbcopy`, print only the report block, and stop.
