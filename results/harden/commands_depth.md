# Commands printed in the README

Checked 2026-09-23T05:04:33Z at commit ee175f7 (branch depth) by `uv run python scripts/harden_commands.py`, in a fresh clone after `uv sync --frozen` and `npm ci` in apps/web and worker, the way a judge would start. Setup: uv sync --frozen exit 0, npm ci (apps/web) exit 0, npm ci (worker) exit 0.

| Where | Command | Result | What happened |
|---|---|---|---|
| README.md:75 | `make new-city` | not run | make new-city is not on the safe list |
| README.md:122 | `make diagrams` | pass | uv run python scripts/check_diagrams.py diagrams: 6 Mermaid block(s) parse, by the structural check |
| README.md:270 | `make fhir-validate` | pass | -1.transaction.json 00:00.190 Done. Times: Loading: 00:13.977, validation: 00:01.967 (#7). Memory = 492Mb Done. Times: Loading: 00:13.977, validation: 00:01.967 (#7). Max Memory = 3Gb fhir-validate: 7 file(s), 0 error(s), 37 warning(s), terminology checks ran; details in results/fhir_validation.json |
| README.md:271 | `curl -H "Accept: application/fhir+json" https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466` | pass | venance of one mirrored visit on this server" } ] } % Total % Received % Xferd Average Speed Time Time Time Current Dload Upload Total Spent Left Speed 0 0 0 0 0 0 0 0 --:--:-- --:--:-- --:--:-- 0 0 0 0 0 0 0 0 0 --:--:-- --:--:-- --:--:-- 0 100 2907 0 2907 0 0 4082 0 --:--:-- --:--:-- --:--:-- 4077 |
| README.md:294 | `make judge-check` | fail | judge_check.py", line 132, in step_fhir files = int(data.get("files", 0) or len(data.get("results", []) or [])) ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ TypeError: int() argument must be a string, a bytes-like object or a real number, not 'list' make: *** [judge-check] Error 1 |
| README.md:319 | `make check` | fail | (ran with SKIP_TAP=1: the tap target step on port 3100 skipped) make: *** [verify-claims] Error 1 |
| docs/ACCEPTANCE.md:12 | `uv sync` | pass | Resolved 96 packages in 4ms Checked 91 packages in 2ms |
| docs/ACCEPTANCE.md:13 | `cd apps/web && npm install && cd ../..` | pass | up to date, audited 383 packages in 693ms 146 packages are looking for funding run `npm fund` for details found 0 vulnerabilities |
| docs/ACCEPTANCE.md:23 | `make test` | pass | ........................ [ 70%] ........................................................................ [ 80%] ........................................................................ [ 90%] .............................................................s....... [100%] 716 passed, 1 skipped in 48.79s |
| docs/ACCEPTANCE.md:24 | `make worker-check` | pass | 5ms) ✔ fhir_referral: the ServiceRequest and the example result, the same as Python (2.780458ms) ✔ walks: the same demo Bundle as Python, tagged on every resource, and structurally sound (1.585209ms) ℹ tests 10 ℹ suites 0 ℹ pass 10 ℹ fail 0 ℹ cancelled 0 ℹ skipped 0 ℹ todo 0 ℹ duration_ms 107.995292 |
| docs/ACCEPTANCE.md:26 | `make verify-claims` | fail | s/fhir_validation.json#/files_validated README shows 14, results say 7; run scripts/render_readme.py rendered number drifted: results/fhir_validation.json#/walk_records_validated README shows 2, results say 0; run scripts/render_readme.py verify-claims: 2 problem(s) make: *** [verify-claims] Error 1 |
| docs/ACCEPTANCE.md:27 | `make audit-verify` | pass | uv run python scripts/verify_audit.py audit-log: 3 entries, chain intact, last hash 3d3cbb4da01ac26e9e9579dac9681d67e5b034006cfc1ddd4215ea28d0fb3cc3 |
| docs/ACCEPTANCE.md:28 | `make manifest-check` | pass | uv run python scripts/check_manifest.py manifest-check: 84 image(s), all with matching rows |
| docs/ACCEPTANCE.md:29 | `make readability` | pass | uv run python scripts/check_readability.py readability: 97 strings, average grade 5.20 (cap 7.0), hardest 11.0 (cap 11.0), 3 exception(s) |
| docs/ACCEPTANCE.md:30 | `make dash-check` | pass | uv run python scripts/check_dashes.py dash-check: no em or en dashes in tracked files |
| docs/ACCEPTANCE.md:32 | `make design-check` | pass | (ran with SKIP_TAP=1: the tap target step on port 3100 skipped) cd apps/web && node scripts/design-check.mjs design-check: clean. 70 source files and 23 content files scanned, contrast computed from tokens.css, tap targets skipped (SKIP_TAP=1). |
| docs/ACCEPTANCE.md:33 | `make web-build` | pass |  /quick ├ /share/[score] │ ├ ● /share/0 │ ├ ● /share/1 │ ├ ● /share/2 │ └ ● [+14 more paths] ├ ○ /spot ├ ○ /t ├ ○ /two ├ ○ /walk └ /walk/[id] ├ ● /walk/v02 ├ ● /walk/v03 └ ● /walk/v07 ○ (Static) prerendered as static content ● (SSG) prerendered as static HTML (uses generateStaticParams) web build ok |
| docs/ACCEPTANCE.md:35 | `make preflight-launch` | pass | 3 NOTE second_labels: no second label for test photo ph-pipe-04 NOTE key_agreement: one labeller set the whole key, so no agreement figure is reported: named in docs/analysis_plan.md and under Known weaknesses checks: 17 run, 15 passed, 0 failed, 17 notes preflight: 0 failed, of which 0 need a human |
| docs/ACCEPTANCE.md:36 | `make submit-check` | fail | nnot tell if the repo is public (gh said: none of the git remotes configured for this repository point to a known GitHub host. To tell gh about a new GitHub host, please use `gh auth login`) submit-check: 4 failed: video_link, secrets_scan, verify_claims, repo_public make: *** [submit-check] Error 1 |
| docs/ACCEPTANCE.md:43 | `cd apps/web && npx playwright test` | not run | serves the app on port 3100, which another session uses on this machine |
| docs/ACCEPTANCE.md:44 | `make worker-e2e` | pass | ) [wrangler:info] GET /api/two 200 OK (6ms) [wrangler:info] POST /api/check/draft 422 Unprocessable Entity (1ms) [wrangler:info] POST /api/check/draft 422 Unprocessable Entity (2ms) [wrangler:info] POST /api/check/finalize 404 Not Found (2ms) [wrangler:info] POST /api/check/draft 404 Not Found (3ms) |
| docs/ACCEPTANCE.md:45 | `DEPLOYED_URL=... DEPLOYED_API=... npx playwright test tests/deployed-smoke.spec.ts` | not run | a template with a placeholder in it, not a command to run as printed |
| docs/ACCEPTANCE.md:46 | `SITE_URL=... node apps/web/scripts/live-check.mjs` | not run | a template with a placeholder in it, not a command to run as printed |
| docs/ACCEPTANCE.md:78 | `uv run pytest -q scripts/tests/test_no_video_files.py` | pass | .. [100%] |
| docs/ACCEPTANCE.md:79 | `SITE_URL=https://second-look-79t.pages.dev node apps/web/scripts/live-readonly.mjs` | not run | not on the safe list |

25 commands: 16 pass, 4 fail, 5 not run.
