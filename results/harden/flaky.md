# Flaky tests

Measured 2026-09-24T11:37:55Z at commit 198af9b by `uv run python scripts/harden_flaky.py --runs 3`, in a fresh clone outside the repo. A test is flaky when its outcome differs between runs.

## Runs

| Run | Suite | Exit | Seconds | Outcomes |
|---|---|---|---|---|
| 1 | pytest | 0 | 193.7 | 1993 passed, 2 skipped, 9 xfail |
| 1 | worker golden | 0 | 0.3 | 15 passed |
| 1 | worker e2e | 0 | 15.6 | 1 passed |
| 1 | web e2e | 0 | 53.2 | 92 passed, 2 skipped |
| 2 | pytest | 0 | 152.3 | 1993 passed, 2 skipped, 9 xfail |
| 2 | worker golden | 0 | 0.2 | 15 passed |
| 2 | worker e2e | 0 | 13.2 | 1 passed |
| 2 | web e2e | 0 | 48.2 | 92 passed, 2 skipped |
| 3 | pytest | 0 | 148.7 | 1993 passed, 2 skipped, 9 xfail |
| 3 | worker golden | 0 | 0.2 | 15 passed |
| 3 | worker e2e | 0 | 13.0 | 1 passed |
| 3 | web e2e | 0 | 47.4 | 92 passed, 2 skipped |

## Flaky

None. Every test had the same outcome in all 3 runs.
