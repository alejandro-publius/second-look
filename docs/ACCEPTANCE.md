# Acceptance

What "done" means for Second Look, as checks anyone can run. Each line is one command and the line of output that means it passed.

| # | What | Command | Passes when it prints |
|---|---|---|---|
| 1 | Everything a contributor runs | `make check` | `CHECK GREEN` |
| 2 | The one command for a judge, no key, no network | `make judge-check` | five lines, none failed |
| 3 | Every emitted resource validates against the pinned guide | `make fhir-validate` | `0 error(s)` |
| 4 | Every number in the README traces to `results/` | `make verify-claims` | `all match results/` |
| 5 | The audit log chain is intact | `uv run python scripts/verify_audit.py` | `chain intact` |
| 6 | Every image has a manifest row | `make manifest-check` | `all with matching rows` |
| 7 | No em or en dash anywhere | `make dash-check` | `no em or en dashes in tracked files` |
| 8 | Every visible string reads at about age 12 | `make readability` | no string over the cap |
| 9 | The model can never write an answer | `uv run pytest -q core/tests/test_gate.py` | all passed |
| 10 | The Worker behaves end to end with a local D1 | `cd worker && npm run e2e` | exit code 0 |
| 11 | The launch gate for the two-minute test | `make preflight-launch` | 0 failed |
| 12 | The submission gate | `make submit-check` | fails only on `video_link` and `repo_public` until Sep 30, then nothing |
| 13 | The live site answers | open https://second-look-79t.pages.dev/judges on a phone | the judges page loads |
