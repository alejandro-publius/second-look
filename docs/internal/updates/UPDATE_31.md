# Second Look: prompt 31P (the assisted study, built in parallel with prompt 30)

Everything below is addressed to Claude Code.

You are in `~/second-look-assisted`, a git worktree on branch `assisted`, cut from `depth`. Another session is running prompt 30 in `~/second-look-depth` at the same time, deploying and editing the README, the checklist and the Mac jobs. So this run works in two stages.

**Stage 1, now, new files only.** Build everything in sections 1 to 3 below that can live in new files: the part 2 flow under its own route folder, the plan v2 document, the flags script and its results file, the analysis script and its synthetic tests, the power simulation, the new tests, the judge page's demo entry as a new component. Do not edit the README, `docs/internal/DONE.md`, `docs/internal/PLAN_TO_DONE.md`, `docs/deviations.md`, the lock job script, `docs/internal/PANEL_STUDY.md`, the part 1 end screen or any Mac job. Where a change to one of those is needed, write it as a patch file under `docs/internal/patches/assisted/` with a one-line summary. Never deploy. Never tag. Commit and push `assisted` after each piece. `make check` must stay green on this branch.

**Stage 2, integration, only when prompt 30 has finished.** Prompt 30 is finished when a report newer than 2026-09-25T18:00Z exists under `docs/internal/reports/` on `origin/depth` and `depth` has had no commit for 20 minutes. Check every 15 minutes. When it has: merge `origin/depth` into `assisted`, apply your patches, wire the end screen offer line (logged as a deviation), add the checklist lines, extend the lock job, update the panel study text, run `make check`, tag `prereg-v2` with its hash, audit entry and OpenTimestamps proof, merge into `depth` and forward to `main`, deploy in the order in `docs/notes/hosting.md`, run the phone tests for both part 2 arms against production with the QA key, update the status issue, write the report, copy it to the clipboard with `pbcopy`, print the report block, and stop. If prompt 30 is still running at 2026-09-26T13:00Z (06:00 PDT Saturday), integrate anyway, because the panel launches Saturday morning and part 2 must be live first; take care to merge rather than overwrite.

Same rules as always: decide and log, no em dashes, en dashes or emoji, never make the repo public, paid calls not capped.

## 0. What this adds and why

Track 3's own words: "use AI responsibly to support stream assessment without replacing human judgment." Every proof so far shows the AI is kept in its place. This study measures whether its one question makes a person more accurate. Save this text as `docs/internal/updates/UPDATE_31.md`. Every section becomes RED lines in `docs/internal/DONE.md`. Same rules as prompt 30; the two-minute test's frozen flow does not change, and part 2 begins only after the end screen of part 1, as a logged deviation to the end screen.

## 1. The design, fixed now

- **Who:** everyone who finishes part 1 through the public link or the panel, in either arm. Part 2 is offered after the score screen with one line: "Eight more photos, two minutes, and this time a checker may ask you to look again." They can decline; a decline is recorded and analysed as not started.
- **Items:** the eight spare photos in the manifest, two per feature, one present and one absent, never shown in the lesson or the test, each with its gold label. Freeze their ids and question wording in the plan. The question wording is the same as part 1's per feature.
- **Randomization:** 1 to 1, server side, permuted blocks of 4, stratified by part 1 arm, into `assisted` and `unassisted`. Stored with the session.
- **Assisted flow, per item:** the person answers first. If the checker's flag for that item (computed at build time from the committed pass table and the models' stored answers, only on features the model passed) disagrees with the person's answer, one question appears: "The checker noticed something here. Look again?" with Keep or Change. If it agrees, or the feature was not passed, nothing appears. The person's final answer is the one scored.
- **Unassisted flow:** the same eight items, no questions.
- **Stored per item:** first answer, final answer, whether a question was shown, the choice made, and the timings. No model call at runtime: every flag is precomputed and committed, so the assistance is identical for every participant.
- **Primary outcome:** per-participant accuracy on the eight items (final answers), assisted minus unassisted, two-sided permutation test, 10,000 permutations, bootstrap 95 percent interval, seed 20260926. One confirmatory test.
- **Secondary, descriptive:** among assisted participants, how often a question was shown, how often the answer changed, and the accuracy of changed answers versus kept ones; accuracy by feature; accuracy by part 1 arm; time per item; the share of Can't tell.
- **Exclusions, decided now:** did not finish all eight items; finished the eight in under 20 seconds; QA sessions; sessions after the lock.
- **Data lock:** the same instant as plan v1, 2026-09-28T01:00:00Z. Nothing is read before it.
- **Sample size note:** with about 40 per arm, a difference of about 12 points is detectable at 80 percent power for eight items; below 20 per arm, the result is reported as a description. Write the simulation as `evals/power_v2.py` and cite its file.

## 2. Build it

1. `docs/analysis_plan_v2.md` with the design above in the plan's usual sections, committed and tagged `prereg-v2` before any part 2 session exists, with its SHA-256 in `docs/notes/plan_hash.md`, an audit entry, and an OpenTimestamps proof.
2. The precomputed flags: `evals/assist_flags.py` writes `results/assist_flags.json` from the models' stored answers on the eight items and the pass table, and a test proves that a feature the model did not pass never produces a flag.
3. The part 2 flow at `/t2`, reached only from the part 1 score screen, with the offer line, the randomization, the two flows, the storage, and the end screen showing the eight-item score. Resume and resend work as in part 1. The end screen's offer line is the only change to part 1, logged in `docs/deviations.md`.
4. `evals/assist_analysis.py`, written and tested on synthetic data before the tag: a scenario where the question helps, one where it does nothing, and one where people change to the wrong answer when asked; the script refuses real data before the lock and without the tag, exactly like part 1's.
5. The lock job from prompt 30 runs this analysis too, right after part 1's, and fills a second human row in the README's numbers table: "Does the checker's question help? assisted N, unassisted N, difference, interval", or the sentence that too few finished part 2.
6. `docs/internal/PANEL_STUDY.md` updated: about 8 minutes, payment raised to match, the description mentions the optional second block, the same completion code shown at the end of part 2 and at the end of part 1 for those who decline.
7. `make panel-status` shows part 2 counts by arm.
8. The README: one paragraph under Evals describing part 2 and its tag, and the Track 3 statement gains one sentence: the AI's help is measured, not assumed. The video's voice script gets one line for it if a beat can carry it without cutting anything.
9. On `/judges`: "Assisted second look, try it" opens `/t2` in demo mode with feedback and nothing stored, so a judge feels the question.

## 3. Proofs

- The fuzz test extended: no matter what the precomputed flags contain, the stored final answer is the person's choice, and a flag never changes an answer by itself.
- A test that part 2 cannot be reached before part 1's score screen.
- The phone end-to-end test for both part 2 arms against production with the QA key, including a Change and a Keep.
- The judge-check and done-check lines for all of the above.
