# Second Look: prompt 18 (the conductor that finishes the project)

Paste this whole file into a new Claude Code session on the `alejandro-publius/second-look` repo. It replaces prompt 17. Everything below is addressed to Claude Code.

## 0. Where you are, what the planner verified, and the one rule

Alex is at work and reads your progress on his phone. Other sessions on his Mac may still be running: prompt 15 on branch `depth` (resuming UPDATE_14, and it pushes to `main` too) and possibly prompt 16A on branch `harden`. You may be on his Mac or in the cloud. If `~/second-look-depth` exists you are on the Mac; otherwise you work from a fresh clone and cannot deploy, run paid models or reach his files, so list those steps for him instead.

**The one rule: never push to a branch someone else is working on.** A branch is busy if its newest commit on GitHub is less than 30 minutes old, or, on the Mac, if its worktree has a file modified in the last 20 minutes or a `claude` process is running in it. Re-check before every push. Work on your own branches and bring changes in through pull requests.

For the whole run: never make the repo public, never touch the production database, never delete by search or `$expunge` on their sandbox, never call `api.enora-oah.eu`, no em dashes, en dashes or emoji. Read `CLAUDE.md` and `PLAN.md` first. Save this text as `docs/internal/updates/UPDATE_18.md` on your first branch. Decide instead of asking, and write each decision in the status issue.

What the planner verified in the repo snapshot and in GitHub's notification emails, as of 17:38 UTC today:

- The `check` workflow has failed on every push to `main` since Sep 21, most recently run 35761740532 on commit 284f461. `main`'s `.github/workflows/check.yml` is missing three things that `depth`'s has: the step `cd apps/web && npx playwright install --with-deps chromium` (design-check drives the built app in Chromium, so `make check` fails without it), the steps `cd worker && npm ci` then a Node 22 setup and `cd worker && npm run e2e`, and `worker/package-lock.json` in the npm cache paths.
- `main`'s `.github/workflows/backup.yml` still runs on a daily schedule (`cron: "20 9 * * *"`) and fails every time, because backups run on the Mac through launchd and the GitHub secrets were never added.
- The pull request from `depth` was green on Monday afternoon and failed again at commit d036065 at 06:02 UTC today, during the session that ran out of API credit.
- No GitHub activity after 17:38 UTC.
- The Monday snapshot of `depth` still had: `DEMO_URL_PLACEHOLDER` in the README, `content/approved_sentences.yaml` with `sentences: []` (so `/city` and the health card show nothing), `fly.toml`, and the planning prompts mixed into `docs/`. UPDATE_14 phase 2 was meant to fix all four. Check whether it did.

## 1. A live status issue (first 15 minutes)

Gather the truth from GitHub and the live site:

- Every branch with its newest commit, time and message; open pull requests and their checks; whether the tag `prereg-v1` exists.
- The last 10 runs of every workflow, and for the newest failure on each branch, the cause from `gh run view <id> --log-failed`, in one line.
- The newest report on each branch under `docs/internal/reports/` or `docs/reports/`, in three lines.
- The live site from `docs/notes/hosting.md`: `/` answers, `/demo` shows the shut page, the counts endpoint answers.
- UPDATE_14 phases 1 to 9, each marked done, partly done, not started or failed, with evidence.
- The four items from the Monday snapshot above, each fixed or not.

Create a GitHub issue "Status: Second Look" with a checklist and one plain paragraph at the top. If it exists, edit its body. Update it at the end of every section with the time. If `gh` cannot create issues where you are, keep the same text in `docs/internal/STATUS.md` on your branch and in your pull request description.

## 2. CI green on main and depth

1. On a branch `ci-main` cut from `main`, change only files under `.github/workflows/`: bring `check.yml` in line with `depth`'s version (the three items above), and make `backup.yml` manual only (`workflow_dispatch`) with a comment saying backups run on the Mac. Open a pull request into `main`. When its checks pass and `main` has been idle for 30 minutes, merge it. A workflow-only change cannot affect the live site. Change nothing else on `main` in this run.
2. On a branch `ci-depth` cut from `depth`: find the cause of the d036065 failure and of any newer failure from the logs, fix it, make `backup.yml` manual only there too, and check whether CI depends on anything that exists only on the Mac (the video cache, `~/second-look-backups`, `.env`, a local database, a launchd job). Make CI independent of all of it. Open a pull request into `depth`; merge it when green and `depth` is idle.
3. If a branch stays busy, leave the pull request green and ready and say so in the issue.

## 3. Kits for when Alex is back (new files only, always safe)

On branch `finish` cut from `depth`, create new files only, never edit an existing one. If prompt 15 already made something similar, build from it and say at the top of yours that it supersedes it.

1. `docs/video/VOICE_SCRIPT.md`: the exact words for a 3:45 video at about 150 words a minute (520 to 580 words), one beat per row with its time and screen. Open on the two creek photos and the question. Plain words. Every number from `results/` or the README; where none exists yet, a marked slot, never a guess.
2. `docs/video/teleprompter.html`: one self-contained local page, very large text, scrolls at speaking pace, space to pause, a speed control.
3. `docs/video/CREEK_30_MIN.md`: 30 minutes at Strawberry Creek on the UC Berkeley campus: the shots with durations, where to stand, what to avoid (faces, plates, house numbers), and one real creek check in the app.
4. `docs/submission/DEVPOST_PASTE.md`: every Devpost field in its own code block so it copies with one tap: name, tagline under 200 characters, the track statement as line one, the description under the organizers' five headers (the problem; alignment with OneAquaHealth; innovation and practical value; effective use of data, technology, AI, APIs and standards; a clear demonstration), users and impact on ecosystem and human health, built with, the live link, the `/judges` link, the repo link, a video slot. Character counts. Run `scripts/verify_claims.py` over it.
5. `docs/submission/JUDGE_QA.md`: the 20 hardest questions by kind of judge (freshwater ecologist, FHIR standards, agents and MCP, digital health and outreach, engineering, blockchain), each with a short honest answer and the file or command that proves it.
6. `docs/internal/upstream/`: the contribution to `hl7-eu/oah`, ready for when the repo is public: the FSH example, the pull request text from `docs/ig_proposal.md`, and the commands to fork, branch and open it.

Commit and push after each file. Open a draft pull request from `finish` into `depth`: "Finish: video, Devpost and judge kits".

## 4. Take over the build if prompt 15 has stopped

Prompt 15 has stopped if `depth` has had no commit for 60 minutes and, on the Mac, no file in `~/second-look-depth` changed in the last 20 minutes and no `claude` process runs there. If it has stopped and its newest report does not show UPDATE_14 complete:

1. Find UPDATE_14 in the repo (`docs/internal/updates/` or `docs/updates/`). Work on a branch `takeover` cut from `depth`.
2. Finish UPDATE_14 phase 2 first if the Monday items are still open: approve the ten sentences it names with `approved_by: "Alex Velazquez"` and a note that the planner checked them against their sources on 2026-09-21; say on `/city` and in the README that the city actions are OneAquaHealth's own restoration measures from the OneAquaHealth Policy Brief (2026), page 9; delete `fly.toml` and every live mention of Vercel and Fly; move the planning notes into `docs/internal/`; remove the README placeholders.
3. Then continue from the first unfinished step of phases 3 to 8. The AI runs (phase 3) need `ANTHROPIC_API_KEY` in `~/second-look-depth/.env` on the Mac: if you have it, run them within UPDATE_14's 40 dollar cap, counting what `results/cost_log.jsonl` already shows; if not, build against the fake client and put the one command Alex must run at the top of the status issue. Deploys (phase 6) only on the Mac, in the order in `docs/notes/hosting.md`, with the phone end-to-end tests against production after each step; in the cloud, prepare the pull request and list the commands.
4. `make check` wherever you can, commit and push after each phase, pull request into `depth`, merged when green and `depth` is still idle.

If prompt 15 is still running, skip this section and say so.

## 5. Harden, once the build is done

When UPDATE_14 is complete (by prompt 15 or by you), on a branch `harden-fixes`:

1. If branch `harden` exists and is idle, merge it, and apply its patches from `docs/internal/reviews/patches/` in order. Skip any that touch the two-minute test flow or the study endpoints, and list them.
2. If `docs/internal/reviews/JUDGE_SIM_00_before.md` does not exist, run the judge simulation now: six subagents, one per kind of judge above, each with the README, the live `/judges` link, the rubric from `docs/internal/MASTER_BRIEF.md` section 2 and no more than 8 screenshots, each giving a score from 1 to 10 per criterion with a reason, the three things they would find thin, and one change that would raise a score.
3. Fix every item that costs under an hour and does not touch the test flow, most valuable first. Put the rest in the README's Known weaknesses or `docs/JUDGE_SCORECARD.md`.
4. Run the simulation again and record the change in each score in `docs/internal/reviews/JUDGE_SIM_01_after.md`.
5. On the Mac with the key, if the current models page lists a newer Opus model than those in `evals/models.yaml`, add it as one more observer on the 16-photo test and the labelled frames, within 10 dollars, and update the README tables with the date.
6. Pull request into `depth`, merged when green and idle.

## 6. The last update

Rewrite the top of the status issue as the first thing Alex reads when his shift ends: what finished, what is green, what is waiting on what, and the one command to run when he sits down. Then add `docs/internal/WHEN_ALEX_IS_BACK.md` to `finish` with at most 10 steps in order, each with its command and minutes, none of them something software could have done. Link every pull request and new file in the issue. On the Mac, also copy the top paragraph to the clipboard with `pbcopy`. Then stop.
