# Second Look: prompt 15 (fresh window, resume UPDATE_14)

Everything below is addressed to Claude Code.

You have no memory of earlier work, so start from the files. Work in `~/second-look-depth` (branch `depth`), and for this run you also own `~/second-look` (branch `main`, the live launch build). No other Claude Code window is open.

1. Read `CLAUDE.md`, `PLAN.md` and `docs/HANDOFF_NEXT.md` in both worktrees. Then find `UPDATE_14.md`, under `docs/updates/` or `docs/internal/updates/`. UPDATE_14 is the brief for this run and its rules apply, with this message on top of it.
2. What happened. A previous session was running UPDATE_14 and stopped part way through phase 3 (open creek footage: the video finder was being built, videos had been cached outside the repo and frames sampled) when the API balance ran out. The worktree may hold uncommitted changes, and subagents were writing at the same time, so some files may be half done.
3. First, `git status` in both worktrees. On `depth`, commit what is coherent in small commits with honest messages. Delete only what is clearly a broken fragment, and say what you deleted. Run `make check` until it is green.
4. Before redoing anything, check what is already done: the tag `prereg-v1` and the deploy of `main` (phase 1); approved sentences and `docs/internal/` (phase 2); `results/`, `videos/`, the benchmark rows in `photos/manifest.csv`, `docs/screens/`, the README (phases 3 and 4). Mark every phase and step as done, partly done or not started in `docs/HANDOFF_NEXT.md` before you start work.
5. Do whatever part of phase 1 is missing. Then continue from the first unfinished step of phase 3 and run every remaining phase of UPDATE_14 to the end.
6. Same rules as UPDATE_14 section 0: decide instead of asking and log each decision in `docs/DECISIONS.md`; `make check`, commit and push after each phase; refresh the handoff; two subagents at most; paid model calls capped at 40 dollars for the whole run, counting what `results/cost_log.jsonl` already shows; if context gets tight, write the handoff and continue in a fresh subagent. If `ANTHROPIC_API_KEY` is missing from `~/second-look-depth/.env`, build the AI steps against the fake client and end the report with the one command Alex must run.
7. Finish with the report from UPDATE_14 section 9: write it under `docs/internal/reports/`, copy the file to the clipboard with `pbcopy`, print only the report block, and stop.
