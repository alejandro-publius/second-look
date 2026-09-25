# Hosting: what was tried, what won, and why

Update 09 section 2. Hosting is Cloudflare only: Pages for the web, a Worker with D1 and KV for the API. Nothing here needs a card.

Cloudflare account: `thealexschroeder@gmail.com`, account id `b8a915bd28ade9fec05659028b395865`.
`npx wrangler whoami` was already logged in, so nothing is waiting on Alex to run a command.

## Web: static export to Cloudflare Pages. This won.

The Next app now builds two ways. The default is still `standalone`, so docker compose, `next
start` and the whole Playwright suite work exactly as before. `npm run export` sets `NEXT_EXPORT=1`
and produces a static `out/` for Pages. Four things had to change:

- `/spot/[id]` became `/spot?id=`, and `/quick/[spot]` became `/quick?spot=`. A static export has
  no server to read a path parameter it cannot know at build time. `components/QueryParam.tsx`
  reads the query with `useSyncExternalStore`, not `useSearchParams`, because that one forces a
  Suspense boundary and a client bail out.
- The share card route and the web app manifest are `dynamic = "force-static"` with
  `generateStaticParams`, so all seventeen score cards are written as files at build time.
- `/demo` stopped reading server search params and reads the query in the browser.
- The security headers moved. `apps/web/security-headers.mjs` is now the single definition, and
  `apps/web/scripts/build-headers.mjs` writes `apps/web/public/_headers` from it for Pages while `next.config.ts`
  uses it for the server build. A static export gets no headers from Next at all, so without this
  the strict policy would have silently vanished on deploy. It is verified live below.

Static export cost about 40 minutes, inside its box, so the OpenNext adapter was never needed.

## API: a TypeScript Worker on D1. The Python Worker did not survive the probe.

The brief's first choice was a Python Worker running our FastAPI app and `core/` as they are.
It fails, for one deep reason and one shallow one.

- **Deep, and decisive: D1 is not a database connection.** FastAPI itself is supported on Python
  Workers through the ASGI entrypoint, and Cloudflare's own docs say synchronous SQLAlchemy ORMs
  work. But a D1 binding is `env.DB.prepare(sql).bind(...).run()`. It is not a DBAPI connection
  and there is no D1 dialect for SQLAlchemy. Our `apps/api/study.py` is SQLModel from top to
  bottom: `db.exec(select(StudySession)...)`. Making that reach D1 means writing a DBAPI shim over
  the binding. That is a real piece of work, not a 90 minute one, and it would sit under the one
  part of the system that must not be wrong.
- **Shallow, but real: the toolchain.** `pywrangler`, which bundles Python Worker dependencies,
  requires uv 0.12.3 or newer. This machine has 0.11.28, and this whole repo runs on `uv run`.
  Upgrading uv nine days from a deadline, to chase a path already blocked above, is a bad trade.

So the brief's stated fallback was taken: `worker/src/index.ts`, a small TypeScript Worker on D1
carrying the study endpoints. The judge-facing endpoints (`/api/spot`, `/api/two`,
`/api/fhir/validation`, `/api/check/*`, `/api/upload`) are still only in the Python app and follow
after launch, which is what the brief allows.

**Randomization is not reimplemented.** `core/allocator.py` uses Python's Mersenne Twister, which
cannot be ported to JavaScript without risking a different sequence, and the analysis plan
promises the assignment can be replayed. So `scripts/seed_arms.py` writes the allocator's own
sequence into an `arm_slot` table and the Worker only takes the next slot.
`core.allocator.replay` still checks every stored assignment.

## One origin: the API behind /api/* on the Pages site (Update 10 answer A1)

On the `depth` preview the browser talks to one origin only. `apps/web/wrangler.jsonc` is the
Pages project's configuration and binds the API Worker as a service named `API`;
`apps/web/functions/api/[[path]].js` and `functions/health.js` hand every `/api/*` and `/health`
request to it unchanged; `apps/web/public/_routes.json` sends only those paths to the Function
and keeps `/api/share/*`, the static share cards, out of it. The export is built with
`NEXT_PUBLIC_API_ORIGIN=""`, so every fetch is a relative path and the policy says
`connect-src 'self'`. `make deploy-preview` does all of it for the `depth` branch. Verified on
2026-09-21 at https://depth.second-look-79t.pages.dev: `/health` and `/api/test/counts` answer
from the Worker, `/api/share/13` is still an SVG file, the CSP header reads `connect-src 'self'`.
Production keeps its dashboard configuration until `main` deploys with this file.

## What is live

| Thing | Where |
|---|---|
| Site | https://second-look-79t.pages.dev (production, from `main`) |
| Preview of `depth` | https://depth.second-look-79t.pages.dev (API on the same origin) |
| API | https://second-look-api.thealexschroeder.workers.dev/health (the bare address answers 404 by design) |
| Database | D1 `second-look`, id `aff80e0b-6165-4e53-96f5-ff15716221df` |
| Photo store | Workers KV `PHOTOS`, id `221e06ab5b54434ab5b4322712128ef3` |

R2 was not used, because it asks for a card. Creek check photos go to KV after downsizing.

## P1, measured on the deployed site

- One row written to the production database and read back: `GET /api/skeleton` returned what it
  wrote plus the row count, out of D1. That probe was removed on Sep 24 (review REVIEW_03 R02): it
  wrote a row on any request, a GET included, and counted the whole table each time.
- First screen on a throttled 4G profile with a 4x slower CPU: **load 1428 ms, largest paint
  760 ms**, against a pass line of 3 seconds. Unthrottled time to first byte was 0.26 s cold and
  0.14 s warm over three tries.
- A whole sitting on a 390 by 844 phone viewport against the real API: all 16 answers sent, score
  screen read "8 of 16 right". The session was marked `is_test` by the `x-qa-key` header, so a
  live check never lands in the study data. Command: `SITE_URL=... node apps/web/scripts/live-check.mjs`.
- The headers really are served: `content-security-policy`, `referrer-policy: no-referrer`,
  `x-frame-options: DENY`, `x-content-type-options: nosniff` and `permissions-policy` all come
  back from Pages, with `connect-src` naming only our own origin and the Worker.
- The export is token gated live: no token returns 404, the right token returns a 2,600 byte zip
  holding `sessions.csv` and `responses.csv` in the contract's schema.

## The judge facing endpoints on the Worker (Update 10 answer A3)

Built on the `depth` branch, not yet deployed. `worker/src/check.ts`, `city.ts`, `uploads.ts`
and `two.ts` port `apps/api/check.py`, `city.py` and `fhir_routes.py`; the pure parts under
`worker/src/core/` are ports of `core/` proved equal to Python by the golden vectors in
`worker/golden/` (`make worker-check`). Storage is D1 (`spot`, `visit`, `check_result`,
`fhir_bundle`, `upload`, `sandbox_cache` in `worker/schema.sql`) and KV for photo bytes with a
30 day expiry. `make worker-e2e` runs the whole thing under `wrangler dev` with a local D1 and
KV, rain from a stub, and drives every route: 9 sections, green on 2026-09-21.

Until the merge, the depth preview's `/api/*` reaches the production Worker, which answers
the study routes and 404s the rest.

## The merge, after data lock (Update 10C answer 2)

The merge waits until after data lock on 2026-09-28T01:00:00Z. Production stays exactly as it is
while strangers take the test: nothing about the study's network path changes mid study. At the
merge, both halves go in one session, in this order, and not the other way round:

1. Apply the new D1 tables. They are additive only, every one is `CREATE TABLE IF NOT EXISTS`:
   `cd worker && npx wrangler d1 execute second-look --remote --file schema.sql`.
2. Deploy the Worker: `bash scripts/deploy.sh worker`, which runs step 1 and then
   `cd worker && npx wrangler deploy`, and writes the new version into the deploy record below.
   The study routes are unchanged in it.
3. Run the study contract tests and the phone end to end tests against production:
   `uv run pytest -q apps/api/tests/test_study.py` for the contract, and
   `SITE_URL=https://second-look-79t.pages.dev node apps/web/scripts/live-check.mjs` on the phone
   viewport with the QA key, so the check lands in no study data.
4. Only then ship the Pages file that puts the API behind the same origin: deploy `main` with
   `apps/web/wrangler.jsonc`, `functions/` and `public/_routes.json`, the export built with
   `NEXT_PUBLIC_API_ORIGIN=""`.
5. Run the phone tests again against production, and check with curl that `/health` and
   `/api/test/counts` answer through the Pages origin, `/api/share/13` is still an SVG, and the
   policy reads `connect-src 'self'`.

`make lock-analysis` (`scripts/lock_analysis.py`), which a launchd job runs at
2026-09-28T01:10:00Z, deploys in this order after the lock's commit, with the read-only phone
check after the site, then confirms judge mode opened, and only then pushes `depth` and `main` in
one atomic push. The push comes last so that a failed step can roll production back to the
deploy record's rows below without rewriting history.

## The sandbox mirror after launch (Update 10C answer 3)

Real creek visits are mirrored once, as one tagged batch after data lock, not as they arrive:
fewer writes on a server everyone shares, and one clean ledger. Two minute test sessions are
never mirrored, because they are not creek observations; the repush script mirrors visit
Bundles only and refuses anything else by shape. The repush runs again just before the video is
recorded, again on Sep 30 and again on Oct 1, because anyone can delete records there. Each run
updates the Library entry's count and its list of Provenances to what that run put on the
server: `SANDBOX_MIRROR_ENABLED=true uv run python scripts/repush_sandbox.py --library
--evidence docs/notes/sandbox_library.md`.

## Deploys and rollback (UPDATE_30 section 7.2)

`scripts/deploy.sh` writes a row here after every production deploy, through
`scripts/deploy_record.py`: the Worker's version id, or the Pages deployment's id with the folder
under `~/second-look-backups/deploys/` that keeps the exact files that went up. Pages has no
rollback on the command line, so going back means uploading those same files again. A row says
`no` until the phone tests have passed against production; then
`uv run python scripts/deploy_record.py good` marks it `yes`, and the record is committed.

`make rollback` prints what it would do: for the Worker, `wrangler rollback` to the newest good
version that is not live; for the site, the newest good build that is not live, uploaded again
with its own commit. `make rollback ROLLBACK=yes` does it, then reads `/health`. D1 tables are
never rolled back; every change to them is additive. `uv run python scripts/deploy_record.py
check-live` exits 0 when what is live now is a good row with its files kept, which the data lock
job checks before it deploys anything.

<!-- deploys:start -->
| When (UTC) | Part | Commit | Id | Archive | Checked |
|---|---|---|---|---|---|
<!-- deploys:end -->

## What is not done

- The rate limit. See docs/DATA_HANDLING.md: it is deliberately absent rather than built on an
  address.
- Deploying the judge facing endpoints: they are built and proved locally, and production
  deploys come from `main` only.
