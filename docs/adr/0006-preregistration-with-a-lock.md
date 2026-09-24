# 0006. The analysis plan is pre-registered, and the code enforces the lock

- **Status:** accepted
- **Date:** 2026-09-21
- **Carried by:** commit 28cdc0b ("The plan is tagged, and the hash is written down"), commit
  1fcc8ec (judge mode's answer route shut until the lock) and commit 8b4b939 (review patch 04);
  `docs/analysis_plan.md` at tag `prereg-v1`, `docs/notes/plan_hash.md`, `core/lock.py`,
  `evals/usability_analysis.py`, `docs/deviations.md`

## Context

A usability result means something only if the analysis was fixed before anyone saw the data. A
promise in a document is not enough: the code has to refuse. A review found that test flags could
run the analysis on real data before the lock (findings F06 to F08), and that judge mode's answer
route could hand out the answer key before the test closed (finding F86).

## Decision

Tag `docs/analysis_plan.md` as `prereg-v1` before the first participant, and pin the tagged commit
and the plan's SHA-256 in the analysis script and in `docs/notes/plan_hash.md`. Keep one data lock
constant, 2026-09-28T01:00:00Z, in `core/lock.py` and in the Worker. The analysis refuses real data
before the lock, without the tag, when the plan differs from the tagged one, or when the tag has
moved, and it reads the real clock and repository, not an option. Judge mode's answer route answers
403 before the lock. Every change after the tag goes into `docs/deviations.md`.

## Consequences

- No outcome is computed before the lock, by anyone, from any copy of the data.
- When the recruited study was dropped on 2026-09-21, that line went into the plan before the tag,
  so it is part of the plan and not a deviation. The lock still guards whatever sessions arrive.
- Fixes to the study routes after the tag, such as the judge mode lock itself, are logged
  deviations with a test on each side of the lock.
