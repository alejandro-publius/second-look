# Deploying and running Second Look

How to run it on your own machine, how to put it on Cloudflare, what the database holds, which
secrets exist (names only), which jobs run on the Mac, and every setting the code reads. The
record of why the hosting looks like this is `docs/notes/hosting.md`; the decisions are in
`docs/adr/`.

## What you need

- Python 3.12 and [uv](https://docs.astral.sh/uv/). `uv sync` installs everything in `pyproject.toml`.
- Node 20 for the web build and Node 22 for wrangler, as CI uses them (`.github/workflows/check.yml`).
  `(cd apps/web && npm ci)` and `(cd worker && npm ci)`.
- Java 17 for the HL7 validator in `make fhir-validate` and `make check`:
  `export JAVA17_HOME=/opt/homebrew/opt/openjdk@17` on a Mac.
- gitleaks for `make secrets`, which `make check` runs (`brew install gitleaks`).
- For a deploy only: a Cloudflare account and `npx wrangler login`. Nothing here needs a card.

## Running locally

| Command | What runs | Network | Data |
|---|---|---|---|
| `make dev` | the Python API on port 8000 with reload, and the site in dev mode on http://localhost:3100 (`WEB_PORT` moves it) | the creek check asks Open-Meteo about rain, and `/two` asks their sandbox; both fail closed when offline | `data/local.db` and `data/fhir_store`, empty at first |
| `make demo-offline` | the same two servers on the same ports, after `scripts/seed_demo.py` fills `data/demo` | none: the seed refuses every socket to another machine and fails if one was tried; the servers get a proxy that goes nowhere | three made up creek checks on Strawberry Creek, two of them by people who passed the test and one with no score; one pipe worth testing; two test sittings that never count |
| `docker compose up` | Postgres, the API and the web server, as in `docker-compose.yml` | as `make dev` | a Postgres volume |

`make demo-offline` needs no key: `ANTHROPIC_API_KEY` is removed before the seed and set empty for
both servers, and nothing on those paths calls a model. The QA key and the export token are
empty too, so nothing can be marked as a test or exported. Open
http://localhost:3100/city?creek=strawberry-creek, then follow a pipe to its record and its FHIR.
Change the ports with `make demo-offline DEMO_API_PORT=8765 DEMO_WEB_PORT=3765`. The first
`uv sync` and `npm ci` are the only steps that use the network. `scripts/tests/test_seed_demo.py`
runs the seed with no key and checks that it tried no socket, marked every sitting as a test and
wrote its audit line into the demo folder.

Both targets keep the audit lines a stored check writes under `data/`, never in the tracked
`audit/log.jsonl`.

### The checks before a commit

`make check` is the gate (lint, types, tests, the manifest, dashes, reading age, diagrams, claims,
the Worker's golden vectors, the FHIR validator, the web build and the design check). It prints
`CHECK GREEN` at the end.

The same fast checks can run on every `git commit` through [pre-commit](https://pre-commit.com):

```
uv tool install pre-commit
pre-commit install
pre-commit run --all-files
```

`.pre-commit-config.yaml` has only local hooks that call this repository's own tools: ruff and
ruff format through `uv run`, `scripts/check_dashes.py`, trailing whitespace, and the secret scan
(`gitleaks git --pre-commit --staged`, then `scripts/submit_check.py --secrets-only`). It never
replaces `make check`.

## Deploying, in this order

Production deploys come from `main` only: `scripts/deploy.sh` refuses any other branch unless
`ALLOW_BRANCH=yes` is set on purpose. The order is the one `docs/notes/hosting.md` fixed, Worker
first and the Pages site last, so the study's network path never changes under a person taking
the test.

1. **The D1 tables.** Every statement in `worker/schema.sql` is `CREATE TABLE IF NOT EXISTS` or
   `CREATE INDEX IF NOT EXISTS`, so applying it again adds what is new and touches nothing else:
   `cd worker && npx wrangler d1 execute second-look --remote --file schema.sql`.
2. **The Worker.** `cd worker && npx wrangler deploy`. Steps 1 and 2 together are
   `bash scripts/deploy.sh worker`, which also writes the new version into the deploy record in
   `docs/notes/hosting.md`, as step 4 does for the site; `make rollback` reads that record.
3. **The contract and the phone tests against production.**
   `uv run pytest -q apps/api/tests/test_study.py`, then
   `SITE_URL=https://second-look-79t.pages.dev QA_KEY=... node apps/web/scripts/live-check.mjs`.
   The QA key marks the sitting as a test; the script reads `/api/test/counts` before and after and
   fails if a real sitting appeared. `node apps/web/scripts/live-readonly.mjs` starts no sitting.
4. **The Pages site.** `bash scripts/deploy.sh web`: it cuts the walk clips from the cache, builds
   the static export with `NEXT_PUBLIC_API_ORIGIN=""` (so every call is `/api/...` on the same
   origin and the policy says `connect-src 'self'`), and deploys `apps/web/out` to the Pages
   project `second-look`. `apps/web/wrangler.jsonc` binds the Worker as the service `API`;
   `apps/web/functions/` hands `/api/*` and `/health` to it; `apps/web/public/_routes.json` keeps
   the static share cards under `/api/share/*` out of the Function.
5. **The phone tests again,** and with curl: `/health` and `/api/test/counts` answer through the
   Pages origin, `/api/share/13` is still an SVG file, and the policy header reads
   `connect-src 'self'`.

The `depth` branch has its own preview: `make deploy-preview` deploys to
https://depth.second-look-79t.pages.dev. Only the pages are its own. The command never changes
the production pages, but the preview's `/api` is the live API and the live database:
`apps/web/wrangler.jsonc` binds the same Worker, `second-look-api`, for a preview as for
production. So a test or a creek check taken on the preview is written into the real data.
Nobody takes the test there. Use it to look at pages, and start a sitting there only with the
QA key, as on production. The preview serves the build it was last deployed from, which can be
older than production; `/sw.js` on each names its build in `VERSION`.

### A new Cloudflare account, once

1. Create the D1 database `second-look` and the KV namespace for photos, and put their ids in
   `worker/wrangler.jsonc` (`DB` and `PHOTOS`).
2. Apply `worker/schema.sql`, then `worker/arms.sql` **once**. `arms.sql` is written by
   `scripts/seed_arms.py` from `core/allocator.py`: it empties `arm_slot`, writes the
   pre-registered arm sequence and makes the counter row. Never apply it to a database people have
   used; the counter row survives, but the sequence is the study's.
   `worker/part2_arms.sql` (`scripts/seed_part2_arms.py`) is the same for part 2's two sequences,
   applied once, only while `part2_slot` is empty.
3. Set the two Worker secrets below with `npx wrangler secret put <NAME>` in `worker/`, from a
   random value (`openssl rand -hex 32`) that you keep in your own `.env`.

## The D1 schema

`worker/schema.sql`, which mirrors `apps/api/models.py` and the Alembic migrations. Times are ISO
8601 text in UTC; booleans are 0 or 1. What each field holds, and what is never stored, is in
`docs/DATA_HANDLING.md`.

| Table | What a row is |
|---|---|
| `arm_slot` | one slot of the pre-registered arm sequence |
| `counter` | the next slot to hand out, one row |
| `session` | one two-minute test sitting |
| `response` | one answer to one test photo in a sitting |
| `observer` | a kept score, under a random contributor token, not linked to the sitting |
| `skeleton_ping` | the first deploy's proof that a row can be written and read back; no route writes it since Sep 24 |
| `spot` | a place on a creek, with its reach and creek, coarse unless the person placed the pin |
| `visit` | one creek check or quick check at a spot |
| `check_result` | one follow-up question a visit asked, and the answer |
| `fhir_bundle` | the validated FHIR Bundle of one finished visit, our store of record |
| `upload` | one photo's id, a hash of its token, its type and size; the bytes are in KV |
| `sandbox_cache` | the laboratory record `/two` shows, as `scripts/cache_their_records.py` fetched it |
| `inaturalist_cache` | one creek's iNaturalist context line: per listed invasive plant, a count, the latest date and a link, as `scripts/cache_inaturalist.py` fetched it |
| `walk_record` | one finished video walk's demo record: the walk id, the coded answers, the time and the demo Bundle, deleted 30 days after it was stored by the Worker's daily cron (`worker/wrangler.jsonc`, 04:17 UTC) and by every new walk; never counted and never mirrored |
| `walk_checks` | the follow-up checks one walk record ran, with the coded answers and the final rating, stored with it and deleted with it |
| `part2_slot` | one slot of part 2's pre-registered arm sequences, one per part 1 arm, from `worker/part2_arms.sql` (`scripts/seed_part2_arms.py`) |
| `part2_counter` | the next part 2 slot per part 1 arm |
| `part2_session` | one part 2, the assisted second look, per part 1 sitting: the part 1 arm, the arm, the item order, or a decline (UPDATE_31) |
| `part2_response` | one part 2 answer: the first answer, whether the checker's question was shown, the choice and the final answer, the timings |

## Secrets

Names only. No value is in the repository: `.env.example` is tracked and `.env` is not, and
`make secrets` scans the history and every file git would commit.

| Name | Where it lives | What it does |
|---|---|---|
| `QA_KEY` | a Worker secret; the ignored `.env` in each checkout | marks a sitting as a test when sent as the `x-qa-key` header, so a live check never counts |
| `EXPORT_TOKEN` | a Worker secret; the ignored `.env` | opens `/api/test/export`; without it the route is 404 |
| `ANTHROPIC_API_KEY` | the ignored `.env` in `~/second-look-depth` only, never exported in a shell | lets `make ai-run` call the models; nothing else reads it |
| `CLOUDFLARE_D1_READ_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | GitHub Actions secrets, not yet set | let `.github/workflows/backup.yml` export D1; the workflow runs by hand only, and only while the repository is private, and it is unused: the daily backup is `com.secondlook.backup` below |
| `wrangler login` (not a variable) | wrangler's own store on the Mac | deploys, the D1 backup and the daily cache job |

Both servers treat a secret shorter than 16 characters as not set (`apps/api/settings.py`,
`sameSecret` in `worker/src/index.ts`). The Python API also refuses the placeholder in
`.env.example`; the Worker does not check for it, so never set a Worker secret to that value.

## Jobs on the Mac

These eight launchd jobs run from one checkout as Alex. The ones that reach D1 or the sandbox use
his wrangler login, and the ones that write to the status issue his gh login, so no job needs a
secret of its own. `make mac-jobs-install` installs all eight from `scripts/mac_jobs.py`, which
holds the table they are built from.

| Label | When | What | Install |
|---|---|---|---|
| `com.secondlook.backup` | daily at 21:00, and at wake if the Mac slept through it | `scripts/backup_d1.sh`: exports D1 to `~/second-look-backups`, outside the repo, and keeps the newest `BACKUP_KEEP` dumps | `make backup-install` |
| `com.secondlook.theirs` | daily at 07:30 | `scripts/cache_their_records.py`: one read only GET to their sandbox, stored in `sandbox_cache` for `/two` | `bash scripts/install_cache_job.sh` |
| `com.secondlook.inaturalist` | daily at 07:45 | `scripts/cache_inaturalist.py`: reads the creeks' Locations from our own API, asks iNaturalist about the region's listed invasive plants near them at one request a second, stores a summary per creek in `inaturalist_cache` | `bash scripts/install_inaturalist_job.sh` |
| `com.secondlook.repush` | daily at 08:00 | `scripts/sandbox_retry.py`: while their sandbox's name does not resolve, sends nothing; when it does, puts our worked visit and Library entry back by conditional create, refreshes `/two`'s cache and says so once on the status issue | `bash scripts/install_repush_job.sh` |
| `com.secondlook.anchor` | daily at 06:00 | `scripts/anchor_audit_head.py`: stamps the audit log's last hash with OpenTimestamps into `proofs/`, but only on a day that hash has changed since the last stamp, sending only that hash to the public calendars; then `scripts/ots_status.py` upgrades every proof and writes `results/ots.json`. It commits nothing | `bash scripts/install_anchor_job.sh` |
| `com.secondlook.hl7` | daily at 09:00 | `scripts/hl7_watch.py`: reads hl7-eu/oah pull request 5 and issues 6, 7 and 8 with `gh`; a new comment from a maintainer goes to the status issue. It never replies | `make mac-jobs-install` |
| `com.secondlook.uptime` | every 10 minutes | `scripts/uptime.py`: GETs `/`, `/judges`, `/city`, one walk, `/health` and the counts on the live site; two failures in a row write `~/second-look-backups/uptime.log`, one status issue comment and a notification | `make mac-jobs-install` |
| `com.secondlook.lock` | once, at 18:10 on Sep 27 in California (2026-09-28T01:10:00Z) | `scripts/lock_analysis.py`: the data lock, `make lock-analysis` | `make lock-analysis-install` |
| `com.secondlook.lock2` | once, at 21:10 on Oct 2 in California (2026-10-03T04:10:00Z) | `scripts/lock_analysis.py --wave 2`: the second data lock, for the second wave of the study, `make lock-analysis-2` | `make lock-analysis-2-install` |

Each one-job installer takes `--remove`. Logs go to `~/second-look-backups/`.
`make rollback` puts the last good deploy back (`docs/notes/hosting.md`).

## Configuration

Every environment variable and setting the code reads, found by `scripts/config_inventory.py`.
`scripts/tests/test_deploy_config.py` fails when the code reads a name that has no row here, when
a row names something the code no longer reads, or when a default below differs from
`apps/api/settings.py`. The Python API reads its settings once, from the environment or `.env`.

| Name | Default | Read by | What it does |
|---|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/local.db` | `apps/api/settings.py`, `apps/api/migrations/env.py`, `scripts/backup_db.sh`, `scripts/restore_db.sh` | the Python API's database: SQLite locally, Postgres in docker compose |
| `EXPORT_TOKEN` | `change-me-long-random`, which counts as not set | `apps/api/settings.py`, `worker/src/index.ts` | opens `/api/test/export` |
| `QA_KEY` | `change-me-long-random`, which counts as not set | `apps/api/settings.py`, `worker/src/index.ts`, `apps/web/scripts/live-check.mjs` | marks a sitting as a test; live-check refuses to run without it |
| `PUBLIC_WEB_ORIGIN` | `http://localhost:3000` | `apps/api/settings.py` | the one origin the Python API allows for CORS; `make dev` sets the dev site's |
| `API_ORIGIN` | `http://localhost:8000` | `apps/api/settings.py`, `scripts/smoke.py` | where the API is, for the compose smoke test |
| `RAINFALL_DRY_MM` | `2.5` | `apps/api/settings.py` | rain in the window, in millimetres, at or under which it counts as dry |
| `RAINFALL_WINDOW_HOURS` | `72` | `apps/api/settings.py` | how far back the rain lookup looks |
| `CHECKER_ENABLED` | `false` | `apps/api/settings.py` | passed to the follow-up selector; the Python API passes it no flags, so even `true` asks no model question today |
| `SANDBOX_BASE_URL` | `https://sandbox.hl7europe.eu/oneaquahealth/fhir` | `apps/api/settings.py`, `apps/api/fhir_routes.py`, `scripts/repush_sandbox.py` | their shared FHIR sandbox |
| `SANDBOX_MIRROR_ENABLED` | `false` | `apps/api/settings.py`, `scripts/repush_sandbox.py` | the mirror writes nothing unless this is `true` |
| `REPO_URL` | `https://github.com/alejandro-publius/second-look` | `apps/api/settings.py`, `scripts/repush_sandbox.py`, `scripts/sandbox_write_test.sh` | named in the user agent and our identifiers |
| `BUILD_HASH` | `dev` | `apps/api/settings.py` | the commit served, stored with every sitting |
| `CONTENT_ROOT` | `.` | `apps/api/settings.py` | where `content/` and `photos/` are |
| `UPLOAD_DIR` | `./data/uploads` | `apps/api/settings.py` | the private folder for re-encoded uploads |
| `AUDIT_LOG_PATH` | `./audit/log.jsonl` | `apps/api/settings.py`, `scripts/repush_sandbox.py` | the hash-chained audit log; the dev targets and the tests point it elsewhere |
| `RANDOMIZATION_SEED` | empty: made at first use and kept in the counter row | `apps/api/settings.py` | the seed of the arm sequence in the Python API |
| `FHIR_STORE_DIR` | `data/fhir_store` | `apps/api/fhir_store.py` | our store of validated Bundles, one file per visit |
| `SANDBOX_CACHE_DIR` | `data/sandbox_cache` | `apps/api/fhir_routes.py` | where the Python API keeps what it fetched for `/api/two` |
| `SANDBOX_THEIRS_CODE` | `dissolved-oxygen` | `apps/api/fhir_routes.py`, `worker/src/index.ts` | which of their laboratory measures `/two` shows |
| `SANDBOX_LEDGER` | `fhir/sandbox_ledger.jsonl` | `scripts/repush_sandbox.py` | the ledger of ids we created there, the only ids we may delete |
| `ANTHROPIC_API_KEY` | none | `evals/model_sweep.py` | the paid model run; read from `.env` or the environment |
| `EVALS_SYNC` | not set | `evals/model_sweep.py` | `1` makes direct calls at the full price instead of one batch per model |
| `JAVA17_HOME` | `/opt/homebrew/opt/openjdk@17` | `scripts/fhir_validate.py` | the Java that runs the HL7 validator |
| `MERMAID_CLI` | not set | `scripts/check_diagrams.py` | `1` also renders every diagram, not only parses it |
| `SECOND_LOOK_BACKUP_DIR` | `~/second-look-backups` | `scripts/preflight.py` | where preflight looks for the last backup |
| `SECOND_LOOK_MEDIA` | `~/second-look-media` | `scripts/fetch_footage.py` | where downloaded footage goes, outside the repo |
| `SECOND_LOOK_SCREENS` | `docs/video/clips` | `scripts/video_final.py` | the screen recordings the final cut uses (`make video-final SCREENS=...` sets it) |
| `SECOND_LOOK_VOICE` | `~/second-look-media/voice` | `scripts/video_final.py` | where a voice file is looked for, outside the repo |
| `SECOND_LOOK_FINAL` | `~/second-look-media/final` | `scripts/video_final.py` | where the final cut, its .srt and the thumbnail are written, outside the repo |
| `SCREENS_API_ORIGIN` | not set | `apps/web/scripts/record-clips.mjs` | the API address a recorded build calls; the mock answers it, so nothing reaches it |
| `SECOND_LOOK_CLIPS` | `~/second-look-media/clips` | `scripts/video_rough.py` | the cut clips the rough cut reads |
| `SECOND_LOOK_SAY_VOICE` | `Samantha` | `scripts/video_rough.py` | the macOS voice of the scratch narration |
| `SECOND_LOOK_CONTACT` | the project's GitHub noreply address | `scripts/find_open_photos.py`, `scripts/find_open_videos.py` | the contact in the user agent of the photo and video searches |
| `WEB_ORIGIN` | `http://localhost:3000` | `scripts/smoke.py` | the web server the compose smoke test reads |
| `DB` | the D1 database `second-look` | `worker/src/index.ts` | the Worker's database binding (`worker/wrangler.jsonc`) |
| `PHOTOS` | the KV namespace for photos | `worker/src/index.ts` | where uploaded photo bytes live, each with a 30 day expiry |
| `ALLOWED_ORIGIN` | not set, which means `*` | `worker/src/index.ts` | the Worker's CORS origin; the site calls it on its own origin, so CORS is not used there |
| `RAIN_URL` | not set, which means Open-Meteo | `worker/src/index.ts` | where the Worker asks about rain; the e2e points it at a stub |
| `E2E_NOW` | not set, which means the real clock | `worker/src/index.ts` | a fixed time for judge mode's lock, set only by `worker/test/e2e.mjs` on its local Workers so both sides of the lock are tested; never set on a deployed Worker (`scripts/tests/test_worker_lock.py`) |
| `API` | the Worker `second-look-api` | `apps/web/functions/api/[[path]].js`, `apps/web/functions/health.js` | the Pages Functions' service binding (`apps/web/wrangler.jsonc`) |
| `ASSETS` | the site's own static files, given to every Pages Function by Cloudflare | `apps/web/functions/walks/[[path]].js` | reads a walk clip, so the function can answer a range request with 206 and only the bytes asked for (UPDATE_32 section 4) |
| `NEXT_PUBLIC_API_ORIGIN` | `http://localhost:8000` | `apps/web/lib/api.ts`, `apps/web/next.config.ts`, `apps/web/scripts/build-headers.mjs` | where the site calls the API; empty means the same origin. Baked in at build time |
| `NEXT_PUBLIC_SITE_URL` | `https://second-look.example` | `apps/web/lib/session.ts`, `scripts/submit_check.py` | the site's own address, for share links |
| `NEXT_PUBLIC_BUILD_HASH` | `dev` | `apps/web/lib/session.ts` | the commit, sent with each sitting |
| `NEXT_PUBLIC_QA_KEY` | empty | `apps/web/lib/api.ts` | set only on a dry-run build, so every sitting it starts is a test; the launch build leaves it empty |
| `NEXT_PUBLIC_PLAN_TAG` | `prereg-v1` | `apps/web/app/how-we-know/page.tsx` | the tag the "how we know" page names |
| `NEXT_EXPORT` | not set | `apps/web/next.config.ts` | `1` builds the static export for Pages; `npm run export` sets it |
| `NODE_ENV` | set by Next | `apps/web/next.config.ts`, `apps/web/components/SwRegister.tsx` | development relaxes the policy and skips the service worker |
| `CI` | set by GitHub Actions | `apps/web/playwright.config.ts` | one retry for a Playwright test in CI, and a test that passes only on its retry still fails the run |
| `WEB_PORT` | `3100` | `apps/web/scripts/web-port.mjs` (read by `apps/web/playwright.config.ts`, `apps/web/tests/helpers.ts`, the design check and the screen scripts), `apps/web/package.json` (`dev` and `start`), `Makefile`, `scripts/judge_check.py` | the port the web app serves on locally; `make judge-check` serves on it when it is free and on a free port it picks when not, and says which |
| `PW_REUSE` | not set | `apps/web/playwright.config.ts`, `apps/web/scripts/design-check.mjs` | `1` lets Playwright use the server already on `WEB_PORT`; only the design check sets it, for the build it has just started there |
| `SITE_URL` | none, must be set (the live site for `make panel-status`) | `apps/web/scripts/live-check.mjs`, `apps/web/scripts/live-readonly.mjs`, `scripts/panel_status.py` | the deployed site the phone checks drive, and the one whose counts `make panel-status` reads |
| `GALLERY_LIVE_URL` | `https://second-look-79t.pages.dev` | `apps/web/scripts/gallery.mjs` | the live site `make screens` photographs, reading only |
| `GALLERY_LOCAL_URL` | `http://127.0.0.1:3217` | `apps/web/scripts/gallery.mjs` | the local build with the mock API for the test flow's screens |
| `GALLERY_RAW` | `apps/web/screens/gallery` | `apps/web/scripts/gallery.mjs` | where the raw captures go before `scripts/make_gallery.py` frames them |
| `API_URL` | `https://second-look-api.thealexschroeder.workers.dev` in live-check; the site itself in live-readonly | `apps/web/scripts/live-check.mjs`, `apps/web/scripts/live-readonly.mjs` | where the phone checks read the counts |
| `WALK_ID` | empty | `apps/web/scripts/live-readonly.mjs` | one walk to check by id |
| `REQUIRE_THEIRS` | not set | `apps/web/scripts/live-readonly.mjs` | `1` fails the read only check when their record is missing |
| `DEPLOYED_URL`, `DEPLOYED_API` | empty, so the spec skips | `apps/web/tests/deployed-smoke.spec.ts` | point the deployed smoke spec at a site |
| `PRECACHE_BUDGET_OUT` | not set, so nothing is written | `apps/web/tests/offline-budget.spec.ts` | where the first visit's background download is written; `make precache-budget` sets it to `results/precache_budget.json` |
| `BUDGET_URL` | `http://127.0.0.1:3100`, or the `WEB_PORT` | `apps/web/scripts/budget.mjs` | the built site the landing budgets measure |
| `LIGHTHOUSE_URL` | `http://127.0.0.1:3100/`, or the `WEB_PORT` | `apps/web/scripts/lighthouse.mjs` | the page Lighthouse measures |
| `SCREENS_URL` | `http://127.0.0.1:3100`, or the `WEB_PORT` | `apps/web/scripts/screens.mjs` and the other screen scripts | the site the screenshots and clips are taken from |
| `SKIP_TAP` | not set | `apps/web/scripts/design-check.mjs` | `1` skips the tap target measurement |
| `POSTER_PORT` | `3102` | `apps/web/scripts/poster.mjs` | the port the poster is printed from |
| `CLIPS_RAW` | a folder under `docs/video/clips` | `apps/web/scripts/record-clips.mjs` | where the raw screen recordings go |
| `README_HTML` | none | `apps/web/scripts/record-clips.mjs` | the rendered README the clip script films |
| `E2E_PORT` | `8791` | `worker/test/e2e.mjs` | the port of `wrangler dev` in the Worker e2e |
| `E2E_COMPAT_DATE` | `2026-08-18` | `worker/test/e2e.mjs` | a compatibility date the local runtime knows |
| `DEMO_URL` | `https://second-look-79t.pages.dev/demo` | `apps/web/scripts/demo-open-check.mjs` | which judge mode page the Sep 28 opening check reads |
| `ALLOW_BRANCH` | not set | `scripts/deploy.sh` | `yes` lets a deploy run from a branch other than `main` |
| `BACKUP_DIR` | `~/second-look-backups` for D1, `data/backups` for the local database | `scripts/backup_d1.sh`, `scripts/backup_db.sh`, `scripts/restore_db.sh`, `scripts/restore_drill_d1.sh` | where backups are written and read |
| `BACKUP_KEEP` | `30` | `scripts/backup_d1.sh` | how many D1 dumps to keep |
| `BACKUP_LABEL` | empty | `scripts/backup_db.sh` | added to a backup's file name |
| `D1_DATABASE` | `second-look` | `scripts/backup_d1.sh`, `scripts/restore_drill_d1.sh` | the D1 database to back up |
| `D1_SCRATCH` | `second-look-restore-drill` | `scripts/restore_drill_d1.sh` | the throwaway database the restore drill fills |

Set in `worker/wrangler.jsonc`, not in the environment: the compatibility date, observability
on, and the two bindings. The web build's security headers are one definition,
`apps/web/security-headers.mjs`, written to `apps/web/public/_headers` for Pages by
`apps/web/scripts/build-headers.mjs`.

## Dependabot

`.github/dependabot.yml` asks each week for updates to the Python packages (through `uv`, from
`pyproject.toml` and `uv.lock`), the npm packages of `apps/web`, of `worker` and of the diagram renderer in `tools/diagrams`, and the GitHub
Actions in the workflows, with a small limit on open pull requests. A Dependabot pull request
runs the same `make check` as any other and is merged by a person, never automatically.
