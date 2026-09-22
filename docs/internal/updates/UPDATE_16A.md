# Second Look: prompt 16A (hardening, the part that can run beside prompt 15)

Everything below is addressed to Claude Code.

You are in `~/second-look-harden`, a git worktree on branch `harden`, cut from `depth`. Another session is running prompt 15 in `~/second-look-depth` at the same time, and it is rewriting the README, the docs, the UI and the Worker. So this run has one rule above all others:

**Additive only.** Never edit, move or delete an existing file. Create new files only, in these places: `docs/internal/reviews/`, `docs/internal/reviews/patches/`, `docs/internal/updates/`, `docs/internal/reports/`, new test files in existing test folders, new files under `results/harden/`, and new scripts named `scripts/harden_*.py`. Never touch `~/second-look` or `~/second-look-depth`. Never deploy anything. Never write to the production database: any load test hits the landing page, the read endpoints and a local `wrangler dev`, never the study endpoints in production. Never make the repo public. Read `CLAUDE.md` and `PLAN.md` first; save this text as `docs/internal/updates/UPDATE_16A.md`.

Where a fix is needed, write it as a patch file under `docs/internal/reviews/patches/NN-<name>.patch` with a one-line summary at the top, and do not apply it. A later session on `depth` applies the patches after prompt 15 finishes.

Commit and push after each section. If `make check` fails only because a new test documents a real bug, mark that test `xfail` with the reason so the branch stays green, and list it in the report.

## 1. Adversarial review, findings only

A subagent that wrote none of the code reads the repo against the hard rules in `CLAUDE.md` and writes `docs/internal/reviews/REVIEW_02.md` with file and line for each finding:

- Any path by which model output could reach a stored answer, a label or a user-facing sentence without the gate, including the Worker port.
- Anything that stores, logs or sends an address, a name, an email, a precise location or a fingerprint.
- Any request that leaves our origin. Any image without a manifest row. Any unapproved sentence that can reach a screen.
- Whether the analysis can run on real data before lock or without the tag. Try it.
- The export token's strength and where it lives. Whether the rate limit ever touches disk or a log.
- Uploads: type check, size cap, private store, 30-day deletion actually scheduled.
- Whether the `is_test` key could be present in a production bundle.
- Every ported Worker function without a golden vector.
- A secrets scan of the tree and of history since `prereg-v1`. `npm audit` and `pip-audit` findings of high severity.

Rank the findings: breaks a hard rule, could lose data, should fix, cosmetic. Each of the first three ranks gets a patch file.

## 2. Judge simulation, the "before" baseline

Six subagents, one per judge type: a freshwater ecologist who leads the project; an HL7 and FHIR standards fellow; an integration program manager who works on agents and MCP; a digital health and outreach person; an IEEE engineering generalist; a member of the IEEE blockchain community. Each gets today's README, the live public link, the rubric from `docs/internal/MASTER_BRIEF.md` section 2 (or `docs/MASTER_BRIEF.md` if it has not moved yet), and no more than 8 screenshots from `docs/screens/`. Each writes: a score from 1 to 10 per criterion with one line of reason; the three things they would find thin; one change that would raise a score; and what they did not understand in the first 30 seconds. Collect into `docs/internal/reviews/JUDGE_SIM_00_before.md` with one score table. This is the baseline; the rebuilt README gets scored again later.

## 3. New tests

A coverage report for `core/`, `apps/api` and `worker/src` into `results/harden/coverage.md`. For any core function under 90 percent, write new test files that raise it. Add property tests for the follow-up selector's two-question cap and for the gate if none exist, in new files. Run the whole suite three times and list anything that flakes in `results/harden/flaky.md`, with what you saw.

## 4. Measurements, no fixes

- Lighthouse on the live `/` and `/judges` on the throttled 4G profile, and on `/city` and one `/walk` if they are deployed. Numbers into `results/harden/lighthouse.md`.
- A load test at 50 sessions a minute for 5 minutes against a local `wrangler dev` of the Worker, plus the live landing page and read endpoints only. p50 and p95 per endpoint into `results/harden/load.md`.
- axe on every deployed screen, phone and desktop, findings into `docs/internal/reviews/A11Y_00.md`, with a patch file for anything serious.
- A link check over the README and `docs/`, dead links into `docs/internal/reviews/LINKS_00.md`.
- Every command printed in the README and in `docs/ACCEPTANCE.md` if it exists: run it and record which ones fail.
- The cost per assessment and per 100 frames from `results/cost_log.jsonl` if it has real rows, into `results/harden/costs.md`.

## 5. Report

Write the report to `docs/internal/reports/<UTC timestamp>-harden.md`: the report block, the findings counts by rank, the number of patch files, the baseline judge table, coverage before and after, the flaky list, the Lighthouse and load numbers, and the exact merge line for the next session (`git merge harden` plus applying the patches in order). Push `harden`, open a draft pull request from `harden` to `depth` titled "Harden: reviews and tests, additive only", copy the report to the clipboard with `pbcopy`, print only the report block, and stop.
