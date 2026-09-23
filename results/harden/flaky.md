# Flaky tests

Measured 2026-09-23T04:45:24Z at commit 5474757 by `uv run python scripts/harden_flaky.py --runs 3`, in a fresh clone outside the repo. A test is flaky when its outcome differs between runs.

## Runs

| Run | Suite | Exit | Seconds | Outcomes |
|---|---|---|---|---|
| 1 | pytest | 0 | 117.6 | 1022 passed, 2 skipped, 11 xfail |
| 1 | worker golden | 0 | 0.2 | 9 passed |
| 1 | worker e2e | 0 | 9.0 | 1 passed |
| 1 | web e2e | None | 0 | not run: needs --web |
| 2 | pytest | 0 | 81.7 | 1022 passed, 2 skipped, 11 xfail |
| 2 | worker golden | 0 | 0.2 | 9 passed |
| 2 | worker e2e | 0 | 8.5 | 1 passed |
| 2 | web e2e | None | 0 | not run: needs --web |
| 3 | pytest | 0 | 79.8 | 1022 passed, 2 skipped, 11 xfail |
| 3 | worker golden | 0 | 0.3 | 9 passed |
| 3 | worker e2e | 0 | 9.7 | 1 passed |
| 3 | web e2e | None | 0 | not run: needs --web |

## Flaky

None. Every test had the same outcome in all 3 runs.

## Seen outside these runs

Added by hand after the runs, because it happened before this script existed. The first coverage run of `scripts/harden_coverage.py` (2026-09-22, about 20:25 UTC, in the worktree while about a dozen review and test-writing agents ran at the same time) ended with 1 failed, 1021 passed, 2 skipped, 11 xfailed. The run's log was not kept, so the test's name is not known. Every run since passed: the rerun of the same command (1023 passed, 1 skipped, 11 xfailed), a plain `uv run pytest` in the worktree, and the three runs above. It is listed here as a failure seen once under heavy load and not reproduced, not as a known flaky test. `scripts/harden_coverage.py` now keeps the pytest log, so a repeat names the test.

The web end to end suite (Playwright, `make e2e`) was not part of the three runs: it serves the app on port 3100, which the other session uses on this machine. CI runs it on every push.

A difference between places, not a flake: in the worktree one test more runs and one fewer is skipped (1 skipped) than in a fresh clone (2 skipped), because a skip depends on an ignored local file.
