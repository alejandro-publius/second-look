# Commands printed in the README

Checked 2026-09-23T04:42:03Z at commit 5474757 by `uv run python scripts/harden_commands.py`, in a fresh clone after `uv sync --frozen` and `npm ci` in apps/web and worker, the way a judge would start. docs/ACCEPTANCE.md does not exist, so only the README was read. Setup: uv sync --frozen exit 0, npm ci (apps/web) exit 0, npm ci (worker) exit 0.

| Where | Command | Result | What happened |
|---|---|---|---|
| README.md:55 | `make dev` | pass | API answered: True; web answered: True. ports 8000 or 3100 are taken by another process on this machine, so the same two servers ran on 8960 and 8961 |
| README.md:57 | `curl -H "Accept: application/fhir+json" https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466` | pass | venance of one mirrored visit on this server" } ] } % Total % Received % Xferd Average Speed Time Time Time Current Dload Upload Total Spent Left Speed 0 0 0 0 0 0 0 0 --:--:-- --:--:-- --:--:-- 0 0 0 0 0 0 0 0 0 --:--:-- --:--:-- --:--:-- 0 100 2907 0 2907 0 0 4771 0 --:--:-- --:--:-- --:--:-- 4765 |
| README.md:57 | `make export-records` | pass | cripts/export_records.py --out data/export export-records: 0 creeks, 0 spots, 0 bundles into data/export warning: `VIRTUAL_ENV=/Users/alexvintera/second-look-harden/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead |
| README.md:57 | `uv run python -m apps.mcp.server --export data/export` | pass | tools: list_creeks, get_creek_record, list_findings, get_observer_score, explain_number |

4 commands: 4 pass, 0 fail, 0 not run.
