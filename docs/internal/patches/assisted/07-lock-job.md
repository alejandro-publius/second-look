Summary: scripts/lock_analysis.py runs the part 2 analysis right after part 1's and fills the README's second human row.

Where: `scripts/lock_analysis.py` as prompt 30 left it, and `scripts/tests/test_lock_analysis.py`.
Written against the file at 5420f3a; apply by hand to the final version.

1. The export step already writes the whole zip; the Worker's export now carries
   `part2_sessions.csv` and `part2_responses.csv` beside the two part 1 files. Unpack all four
   into the export folder.
2. In `analysis()`, right after part 1's `run(...)`, call `evals.assist_analysis.run(input_dir=...,
   out_dir=results, synthetic=False, stamp_name=<the same date stamp>)`. Its guard refuses before
   the lock, without `prereg-v2`, with a changed plan or unpinned hash; a refusal is a failure of
   the lock job, undone like any other. If the export has no part 2 files (part 2 never went
   live), write no result and use the too-few sentence.
3. In `readme()`, put `evals.assist_analysis.readme_row(result)` between `<!-- human-row-2 -->`
   and `<!-- /human-row-2 -->`. Its numbers must be claim tokens pointing into
   `results/assist_<date>.json` (`/primary/n_assisted`, `/primary/n_unassisted`,
   `/primary/difference`, `/primary/ci_low`, `/primary/ci_high`), so verify_claims checks them.
4. Add `results/assist_<date>.json` and `.md` to the files the lock commit may touch, and to the
   `already_done()` test so a second run refuses.
5. The status line on the issue gains: `Part 2: <readme_row>.`
6. Tests, named with part2 so `-k part2` selects them: a lock run on a copy of a database with
   part 2 rows writes the second row with claim tokens; one with no part 2 rows writes the
   too-few sentence; a part 2 refusal undoes the whole run.
