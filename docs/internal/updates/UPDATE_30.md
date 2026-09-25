# Second Look: prompt 30 (the final week, in full)

Alex: quit Claude Code once so the waiting update applies, run `cd ~/second-look-depth && claude`, paste this whole file, then type this line:

```
/goal make done-check has been run in this turn and its full output is in the transcript, ending with "RED: 0"; every BLOCKED line names a cause outside the repo with a date; gh run list output in this turn shows the newest run on main and on depth as completed success; and the top paragraph of the "Status: Second Look" issue lists only HUMAN items with dates. Stop after 300 turns at most.
```

Everything below is addressed to Claude Code.

## 0. Where things stand and how this run works

Read `CLAUDE.md`, `PLAN.md`, `docs/HANDOFF_NEXT.md`, `docs/internal/PLAN_TO_DONE.md`, `docs/internal/DONE.md`, the newest file in `docs/internal/reports/` (UPDATE_29's report from 2026-09-25T05:10Z) and the "Status: Second Look" issue. Save this text as `docs/internal/updates/UPDATE_30.md`.

State on Sep 25: `main` and `depth` are both at eaa7f33, CI green, the site and the Worker deployed and passing the live checks, `make done-check` at RED: 1 (D24) BLOCKED: 5 HUMAN: 9. The submission deadline is Wednesday Sep 30 at 21:00 PDT; Alex submits by 18:00. Judging runs Oct 1 to 15, so the live site must stay up and correct through Oct 15.

Rules for this whole run: work on `depth`, merge forward to `main`, deploy in the order in `docs/notes/hosting.md`, and run the phone end-to-end tests and the read-only live check against production after every deploy. Nothing in the two-minute test flow or the study endpoints changes except where a section below says so as a logged deviation. Decide instead of asking and log every decision in `docs/DECISIONS.md`. Never make the repo public before section 8. Never delete by search or `$expunge` on their sandbox. No em dashes, en dashes or emoji. Up to four subagents in their own worktrees. Paid calls are not capped. Every section below adds or changes lines in `docs/internal/DONE.md`, each with a proving command, and the loop runs until `RED: 0`.

## 1. The five open minors, with acceptance tests

1. **The 24 MB background download.** A first visit to any page must transfer no more than 3 MB in the background. Precache only what the two-minute test needs to work offline: the lesson and practice images at phone size in AVIF or WebP, the test photos at phone size, the fonts, the app shell. Everything else (footage clips, walk media, `/city`, `/two`, the desktop screenshots, the poster) loads on demand and is cached only after it is opened. Acceptance: a Playwright test that opens `/` cold on the phone profile, waits 30 seconds, sums every response body the service worker fetched, and fails above 3 MB; a second test that the test still runs end to end with the network off after that first visit. Record the measured number in `results/` and the README's numbers table.
2. **Back in the middle of a walk loses the answers.** A walk's answers go into the same offline queue the creek check uses, keyed by walk id, so Back, a refresh or a closed tab resumes at the next unanswered question with the earlier answers intact. Acceptance: a Playwright test that answers four questions, presses Back, reloads, and finds all four answers still there.
3. **A walk's record lives only in its browser tab.** Store demo records from walks with the other demo records, tagged as demo, never mirrored, never counted, and visible on `/city` under the demo creek and on `/spot?id=`. Acceptance: finish a walk in one browser context, open its record link in a fresh context, and see it.
4. **The bare `/city` link.** `/city` without a query shows the city picker with every region pack's creeks, and every creek link on the live site resolves. Acceptance: the link checker over the live site plus a Playwright test that opens `/city` and clicks each creek.
5. **judge-check's false failure when port 3100 is busy.** `make judge-check` picks a free port, prints which, and cleans it up afterwards. Acceptance: run it twice at once in two shells and both pass; a test that occupies 3100 first and still sees a pass.

After the five: phone tests against production, and the five lines in `docs/DECISIONS.md` marked closed with the commit.

## 2. The critic rule (D24), changed and then met

The old rule (two consecutive rounds with nothing above cosmetic) cannot be met, because each round finds a few new minors. New rule, logged in `docs/DECISIONS.md` with that reason: D24 passes when two consecutive critic rounds on the same commit report no major finding, and every confirmed minor from those rounds is either fixed or written into the README's Known weaknesses in one plain line each. Confirmed means a second, skeptical agent agreed the finding is real. Run one pair of rounds after section 1, apply the rule, and update `docs/internal/DONE.md`'s D24 line and its check to the new rule.

## 3. Approvals that were waiting on one person

Team approval, Alex Velazquez, Sep 25: the Bay Area invasive plant list is approved as it stands, because every species on it is confirmed against the Cal-IPC inventory with the link recorded in the manifest. Stamp it, run the iNaturalist job today, and prove the context line renders on the Strawberry Creek record and on `/city`. Search the repo for any other gate, flag or TODO that names one person and turn each into a team gate. The blind second label stays optional and stays open.

## 4. The video, ready whether or not the voice arrives

1. Confirm the captions-only final cut exists: under 4:00, 1080p, burned-in captions from the voice script, every footage credit, the CC BY-SA end card, the live link on the end card. Print its path and length. If it does not exist, build it now with `make video-final`.
2. Watch it the way a judge would: extract a frame every 10 seconds and have a critic subagent look at no more than 24 frames for anything wrong (a placeholder, a cut-off caption, a grey card, a stale screen, a wrong number). Fix and re-export.
3. When a voice file appears in the media folder (any of `voice.m4a`, `voice.wav`, `voice.mp3`), `make video-final` lays it over the cut in place of the captions' scratch timing, keeps the captions as subtitles, and re-exports. Document the two commands in `docs/video/README.md`.
4. Write `docs/video/UPLOAD.md`: the title, the description with credits and the CC BY-SA line, the tags, the thumbnail (the two creek photos with the question), and the exact steps to upload to YouTube as unlisted and paste the link into Devpost.

## 5. Data lock and the panel study

1. Install a launchd job for 2026-09-28T01:10:00Z (Sunday Sep 27, 18:10 PDT) and a manual target `make lock-analysis` that does, in order: take a backup; export the study tables; run the pre-registered analysis exactly as tagged, once; regenerate every README number through `scripts/verify_claims.py`; put the human row into the README's numbers table with the count per arm and the source labels, or the sentence that no sessions arrived; `make check`; commit on `depth`; merge forward to `main`; push; deploy; confirm judge mode has opened on production (the shut page is gone and `/demo` answers) and that the phone tests pass; write a line to the status issue. If any step fails, it stops, leaves everything as it was, and writes the failure to the status issue and to `~/second-look-backups/lock.log`. Test the whole chain against a copy of the database with the clock overridden in the test environment, and prove that with the real clock it refuses to run before the lock.
2. `make panel-status` prints completed sessions by source and by arm, and the status issue's top paragraph shows those counts once the panel study is live. If fewer than 20 completed sessions per arm exist at lock, the analysis reports as a description, as the plan says, and the README says so in one line.
3. The ethics step in `docs/internal/PANEL_STUDY.md`: state plainly what the panel asks and what Alex answers, in one paragraph, so it takes him a minute. This is a usability test of our own tool, anonymous, with consent on the first screen, no identifiers stored, and the plan tagged before any participant; nothing about it is clinical or sensitive.

## 6. Their sandbox and the guide

1. The daily repush job keeps retrying the sandbox. If the name resolves again, it pushes the Library entry and the golden visit, updates the cache behind `/two`, and writes a line to the status issue. Test the job's behaviour on both outcomes.
2. Watch `hl7-eu/oah` for replies on the pull request and the three issues (`gh pr view`, `gh issue view`, once a day from the launchd job). If a maintainer asks for a change, make it on the fork branch, keep the guide building, and note it in the README's Contributed back section.

## 7. Judge week readiness, Oct 1 to 15

1. Uptime: a launchd job every 10 minutes hits `/`, `/judges`, `/city`, one `/walk`, `/api/health` and the counts endpoint on production. On two failures in a row it writes to `~/second-look-backups/uptime.log`, comments on the status issue, and shows a macOS notification. Test it by pointing it at a wrong URL once.
2. Rollback: `make rollback` redeploys the last known good Worker version and Pages build, both recorded after every deploy in `docs/notes/hosting.md`. Test it once against the preview deployment.
3. A judge's day: `docs/JUDGE_DAY.md`, the exact path a judge follows in 45 seconds and in 10 minutes, with what they should see at each step, and the fallback if their sandbox is still down (the cached record, the validator output, the screenshots).
4. The demo data is stable: the golden visit, the walk demo creek, the pilot city packs and the region packs must not change after Sep 30 unless a bug is fixed, and the dated jobs (lock analysis, judge mode opening, anchoring, iNaturalist, repush, uptime) must all be running on the Mac with the Mac awake: write `docs/internal/MAC_JOBS.md` listing every job, its time, and the one command that shows it ran today, and tell Alex in `docs/ALEX_TODO.md` to keep the Mac plugged in and awake through Oct 15, with the exact Energy Saver setting.

## 8. Going public and submitting, prepared now, run on Sep 30

1. `make go-public GO=yes` does, in order: a fresh secrets scan of the whole history; removal of `docs/internal/` and every reference to it; `make submit-check`; a check that the README renders with every image reachable and every link answering; the visibility flip with `gh repo edit`; then, after the flip, a second pass from a logged-out session with `curl` that the README, the images, the CI badge and the live link all load publicly. Dry-run it now on a throwaway private mirror of the repo (`gh repo create second-look-dryrun --private`, push, run it there with a flag that skips the flip, delete the mirror) and record the result.
2. `make submit-check` must be red only on the video link and the repo being public until Sep 30, and green after. Add to it: the Devpost text has the track statement as line one, every field is filled, every number matches `results/`, the video link is present, `docs/REPORT.pdf` is attached, and the team lists both members.
3. `docs/SUBMISSION_DAY.md`: the exact order for Sep 30 with times, each step's command, and what to check after each. Include the dry-run submission on Monday Sep 28: fill every Devpost field with the current text, attach the report, save the draft, and read the draft on a phone.
4. A release tag `v1.0` with release notes written from `CHANGELOG.md` in plain words, created by `make go-public` after the flip.

## 9. The last adversarial pass, as a judge

A subagent that wrote none of the product uses the live site the way a judge would, on a phone profile and on desktop, with the network throttled and once with it cut: the 45 second path, the two-minute test, judge mode's shut page, a walk, the creek check with the dry pipe question, a record with View as FHIR and `/verify`, `/city` for Berkeley and one pilot city, `/two`, the credits, `make judge-check` in a fresh clone, and the README top to bottom. It writes `docs/internal/reviews/JUDGE_WALK_01.md` with everything that was slow, confusing, broken or unexplained, ranked. Fix what is above cosmetic. Then rerun the six-judge simulation once and record the change.

## 10. Fallbacks if a human step slips

- No voice by the end of Sep 26 Pacific: the captions-only cut is the video. `docs/video/UPLOAD.md` already describes it.
- No panel study launched by Sep 27 at 12:00 PDT: the lock analysis reports a description with whatever exists, and the README's human row says no sessions arrived.
- No screenshots of the official app: the form stays marked as verified against the app's public text, which the README already says.
- The sandbox still down on Oct 1: `/two` shows the cached record with its date, and the README's outage line stands.
- Alex cannot run `make go-public` on Sep 30 morning: it can be run from any Claude Code window on the Mac; put that sentence in `docs/SUBMISSION_DAY.md`.

## 11. Finish

Merge forward, CI green on both branches, every README link answers, `make done-check` at `RED: 0`, the status issue rewritten with only Alex's items and their dates, the report under `docs/internal/reports/` copied to the clipboard with `pbcopy`, the report block printed. Then stop.
