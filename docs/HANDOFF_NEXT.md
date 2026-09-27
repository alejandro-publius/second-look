# Handoff: where Second Look stands, 2026-09-24

Working notes, kept public on purpose: each section says what was true on its date, and an item
closed since is marked with when and how. What is true now is in the README; the changes and their
reasons are in `docs/DECISIONS.md` and `docs/deviations.md`.

## UPDATE_27 and UPDATE_29, the loop to RED: 0 (Sep 24, 14:00Z)

The definition of done is `docs/internal/DONE.md`; `make done-check` prints PASS, RED, BLOCKED or
HUMAN per line and ends with `RED: <n> BLOCKED: <n> HUMAN: <n>`. The plan is
`docs/internal/PLAN_TO_DONE.md`. Work on `p29/integrate` (worktree `~/second-look-int27`), run
`make check`, `make e2e` and the Worker e2e, then fast-forward `depth` and `main`, deploy in the
order of `docs/notes/hosting.md` (schema, Worker, `live-check.mjs` with the QA key, Pages from
`~/second-look`, then `live-readonly.mjs`). Reading order for a fresh session: `CLAUDE.md`,
`PLAN.md`, this file, `docs/internal/PLAN_TO_DONE.md`, `docs/internal/DONE.md`, the newest
`docs/internal/updates/`.

Where it stands (Sep 27, 06:40Z, after UPDATE_32): `main` and `depth` at b2eaa67, deployed code d107902 (Worker 03d9374e, Pages 1f90ef9f, recorded good); the creek check quotes the official app in its six languages and records the language; `make done-check` RED: 0 BLOCKED: 12 HUMAN: 9; GitHub Actions starts no job (billing, Alex's) so four CI lines are BLOCKED-IF; report `docs/internal/reports/20260927T063000Z-weekend.md`. The paragraph below is the state before it.

Where it stands (Sep 26, 00:10Z, after UPDATE_30): `main` and `depth` at 7dd0ea3 plus the report commit, CI green, Worker d5527e10 and Pages ce38185d recorded good in docs/notes/hosting.md. `make done-check` is RED: 0 BLOCKED: 6 HUMAN: 9; the BLOCKED lines wait on the lock (2026-09-28T01:00:00Z) and their sandbox. Nothing is due from a session before the lock: the lock job on the Mac (Sun Sep 27, 18:10 PDT, from ~/second-look-depth) backs up, runs the tagged analysis once, fills the README's human row, deploys and pushes, and writes to the status issue; uptime, the sandbox retry, the hl7-eu/oah watch, backups, anchoring and iNaturalist run on their own (docs/internal/MAC_JOBS.md). A second session works on UPDATE_31 (the assisted study) in ~/second-look-assisted on branch assisted and integrates once this report is on origin/depth. What is left is Alex's (docs/ALEX_TODO.md) and Sep 30's go-public (docs/SUBMISSION_DAY.md).

Two daily jobs are new on the Mac: `com.secondlook.anchor` (06:00, OpenTimestamps) and
`com.secondlook.inaturalist` (07:45; it asked nothing until the Bay Area plant list was approved
for the team on Sep 25, D66). Their logs are in `~/second-look-backups/logs/`.

Traps: after any change to `content/locales/en.json`, run `scripts/build_worker_content.py`. The
web build rewrites the tracked `apps/web/public/_headers`; restore it before committing. A change
to a README section the report quotes needs `make report-pdf`, and the README cites the report's
page count, so render and rebuild until both settle. A lockfile written by the Mac's npm 11 can
fail CI's npm 10; write lockfiles with `npx -y npm@10`. CI runs on pushes to `main` and `depth`.
Only one process may hold port 3100 (Playwright, the design gate, the flaky and command runs).

## UPDATE_22, after the merge (Sep 24, 04:10Z)

`main` and `depth` are the same commit; keep working on `depth` and move `main` forward with a
fast-forward. CI runs only on pushes to `main` and on pull requests, so a push to `depth` alone is
not checked: run `make check` before moving `main`. Production runs `main`: the Worker (version
4f4cee43) and Pages with the API on its own origin. Keys live only in the ignored `.env` files:
`QA_KEY` in both checkouts, `ANTHROPIC_API_KEY` in `~/second-look-depth/.env`.

Done in this run: the two machine sittings marked as tests (the counts then read 0); the weighting
simulation committed and the README saying what it shows; the paid AI run (6 of 12 features
passed, 13.09 USD of the 40 dollar cap, `results/cost_log.jsonl`; the four-model run later that
day replaced it, and the README has its numbers) and the README's AI table;
smaller AVIF and WebP copies of the two warm-up photos; pull request #8 merged (3 of 21 patches);
open creek footage in the rough cut, credited, and the creek trip removed from Alex's list.

Still open, for a session, as it stood on Sep 24 at 04:10Z. Checked again on Sep 25: F86, F06
to F08, F85, F01 and the warm-up precache item are closed, as each says; F04 and F12 are still
open; F88 is logged in `docs/deviations.md` and its remedy is Alex's.
- Their sandbox's name, `sandbox.hl7europe.eu`, is NXDOMAIN at their own nameserver since Sep 23.
  `/two` shows our record alone and says so; `scripts/cache_their_records.py` runs daily at 07:30
  (launchd `com.secondlook.theirs`) and fills the cache the day the name resolves again. The
  sandbox re-push job on Sep 28, Sep 30 and Oct 1 will fail the same way until then. This terminal
  refused a fetch pinned to their last known address, so none was built.
- Open review findings from pull request #8 (`docs/internal/reviews/REVIEW_02.md`): F86, POST
  `/api/demo/answer` has no server lock check before Sep 28, so 16 POSTs reveal the gold key
  (closed on Sep 24: the route answers 403 until the lock, on both servers, `docs/deviations.md`);
  F06 to F08, the analysis can be run on real data before the lock through test flags (closed on
  Sep 24: patch 04 is applied, `docs/deviations.md`); F85, `person_no_swallow` was drafted by a
  session and carries Alex's name as approver (closed on Sep 23: the sentence was dropped in
  cd50b1d); F88, the gold key came from the planner's picks, and patch 15 asks Alex to label the
  16 test photos blind (logged as a deviation on Sep 24; the blind labels are step 5 of
  `docs/ALEX_TODO.md`); F01, check the Worker's JPEG stripper against REVIEW_02's four GPS photos
  (closed on Sep 24 in bbef994, `docs/deviations.md`); F04 and F12, the favicon's manifest row and
  the IG package sha256 (still open on Sep 25).
- The service worker precaches all ten warm-up copies on a first visit, though a phone shows two;
  `apps/web/scripts/build-content.mjs` could leave them out of `public/precache.json` (closed on
  Sep 25 in fee99f9: the precache now holds one phone-size copy of each photo of the test).
- Beat 9 of the rough cut loops the 9 second extra check recording over 13 seconds, so the phone
  never reaches the dry pipe question the words describe; record a longer clip with
  `make video-clips` before the final cut.
- After Alex records the voice: lay it over the rough cut in place of the scratch voice, keep every
  credit line and the end card (CC BY-SA 4.0), and put the upload link in `docs/devpost.md` and the
  README.

## Update 14 status, end of the prompt 15 run

The brief is `docs/internal/updates/UPDATE_14.md`, resumed by `UPDATE_15.md`. A cloud session
(prompt 18, status issue #4) worked in parallel while this branch sat unpushed; its work is merged
in (7f2b1d5). No API key exists in `.env`, so every AI number waits on the paid run.

| Phase | State |
|---|---|
| 1 Launch on main | done, except two machine sittings in the live D1 table that Alex marks as tests (docs/ALEX_TODO.md step 1) |
| 2 Content and cleanup | done |
| 3 AI on the test and footage | footage, walks and the eval pipeline done; the model gate flags and the paid run are Alex's (step 2) |
| 4 README and docs | done: tier 3 README under the organizers' headers, scorecard, acceptance, architecture |
| 5 How it feels | done: design review 02's safe findings fixed, every screen photographed; the test flow findings and /check's button height left, see DECISIONS |
| 6 Merge and deploy | done on Sep 23 by UPDATE_19: proof, D1 tables, Worker, phone tests, merge, Pages, phone tests again; sandbox checked |
| 7 Video | shot list, recordings and rough cut done; creek footage and Alex's voice are his |
| 8 Submission pack | done: docs/devpost.md, make go-public, docs/ALEX_TODO.md; submit-check fails only on video_link and repo_public |
| 9 Report | docs/internal/reports/, this run |

## Traps found in this run

- Never write a file with `open(p, "w").write(f(open(p).read()))`: the write opens and empties the
  file before the read. It emptied `apps/web/public/sw.js` once; `scripts/tests/test_web_static.py`
  now guards that file.
- A command piped through `tail` exits with tail's code. Gate a commit on the test command itself
  (`set -o pipefail`), or a red test commits.
- Frame and clip screening need macOS: `pyobjc-framework-Vision` is a darwin-only dev dependency.
  Screens are cached in `~/second-look-cache/screens/`; videos in `~/second-look-cache/videos/`.
- Walk clips are never committed. `scripts/deploy.sh web` and `make deploy-preview` cut them from the
  cache with `scripts/build_walks.py --clips-only` and refuse to ship without them.
- YouTube now answers downloads from this machine with a bot check; the footage pool is closed
  until that clears.
- Playwright pads a page into a larger video size; record at the viewport's own size.
- The mock API's finalize refuses what the servers refuse. Keep it that way: a mock that took
  anything hid the rating check bug.

## Live

| Thing | Where |
|---|---|
| Site | https://second-look-79t.pages.dev (from `main`, d6c9d2b), API on the same origin under `/api` |
| Preview of `depth` | https://depth.second-look-79t.pages.dev, API on the same origin, `make deploy-preview` |
| API | https://second-look-api.thealexschroeder.workers.dev/health (the bare address answers 404 by design) |
| Database | D1 `second-look`, id `aff80e0b-6165-4e53-96f5-ff15716221df` |

## What is done on `depth`

- **Update 13** (2026-09-21). Fourteen sentences are approved in `content/approved_sentences.yaml`
  with the approver, the date and the source quotes; `/city` shows what the creek needs from
  OneAquaHealth's own measures and the health card shows one action each for the person, the pet
  and the city (`docs/screens/city.webp`, `11-spot-health-card.png`). The source of the
  city actions is named on `/city` and in the README. The proposal mentions the `morophology`
  spelling. Hosting is Cloudflare only: `fly.toml` is gone and `scripts/deploy.sh` deploys the
  Worker and the Pages site from `main` in the merge order. The planning notes live in
  `docs/internal/` (brief, updates, reports, reviews, kill tests, ledger, build log, depth map,
  team pack, recruiting messages, day plans); every live path points there; new reports go to
  `docs/internal/reports/`. The README carries no placeholder, no gray image and no synthetic
  number: the results section says results arrive with the model run. Tier 3 of Update 10 runs
  the day UPDATE_12's numbers exist; the real warm-up photographs exist on no branch yet.

- `docs/internal/DEPTH_MAP.md`: every feature, read out of the repo. 45 built, 3 parked, 6 missing.
- **Update 10C.** Draft pull request #1, "Depth: do not merge before data lock", exists so CI
  runs on every push to `depth`; it stays a draft. The merge order after data lock is written in
  `docs/notes/hosting.md` (Worker first, phone tests, then the Pages file, phone tests again).
  The sandbox mirror schedule is there too: one tagged batch after data lock, again before the
  video, on Sep 30 and on Oct 1, never a test session. `scripts/repush_sandbox.py --library`
  now updates the Library entry that exists by a conditional update on our own identifier, and
  its count and list are what that run put on the server. The downstream note is pinned by
  golden vectors like every other port: 111 cases, 9 TypeScript suites.
- `core/act.py`: findings from visits, what a creek needs, pipes worth testing, the duplicate pin
  guard, the test pin guard, the downstream note. Pure, 21 tests, every guard mutation tested.
- `GET /api/city/{creek_id}` and `/city?creek=`: the analyst's view. No number without its
  Bundle links. An unapproved measure is absent and the page says why.
- A pin within 30 metres of an existing precise spot is offered on the draft response. A coarse
  pin is never compared, because its position is rounded to about a kilometre.
- **The referral and the way back** (`core/fhir_referral.py`, Update 10B). A pipe on the worth
  testing list has a ServiceRequest at `GET /api/fhir/referral/{spot_id}`: subject the pipe's
  Location, reasons the two people's Observations, requester our Organization. Computed on request
  from stored visits, never stored, so never counted. `.../example-result` is a Specimen under their
  SpecimenOah profile and a three line panel under their indicator profile pointing back at the
  same ServiceRequest and Location. Every laboratory resource is tagged `example` and says EXAMPLE;
  `/city` shows it behind a button with a badge and a notice. Both shapes are golden files in
  `fhir/golden/` and pass the HL7 validator with 0 errors. `docs/REAL_VS_SYNTHETIC.md` lists them.
- **The downstream note** (`core/regions.py`, Update 10B answer 1). The region pack lists
  Strawberry Creek's seven reaches by hand, hills first, each with `flows_into` and an approximate
  box. A stored spot keeps its generated ids; `core/regions.py` places it on a creek and a reach at
  read time, so `/city?creek=strawberry-creek` works and a fix to the pack fixes every old spot. A
  finding on a reach adds one line to every reach below it, with the visit ids behind it, on
  `/city` and on the downstream spots' own records. A coarse pin is placed on the creek only, so it
  counts and neither gives nor gets a line. `/api/city/strawberry-creek` answers before anyone has
  checked the creek, with the reaches and zero visits.
- **Write back** (Update 10 tier 2 item 1). The worked Strawberry Creek visit is mirrored to
  their sandbox: 14 conditional creates, our tag on every resource, ids 452 to 465 in
  `fhir/sandbox_ledger.jsonl`. Our Library entry under their LibraryOah profile is `Library/466`
  there: it names the repository, the read only endpoint, the golden visit and `Provenance/465`.
  `docs/notes/sandbox_library.md` holds what the sandbox returned plus the by tag searches, and
  `docs/notes/sandbox-library.png` is the screenshot. `scripts/repush_sandbox.py` gained
  `--bundle`, `--library` and `--evidence`, and mirrors visit Bundles only: a referral, an example
  or a transaction file is refused by name and skipped in a folder.
- **The MCP server** (`apps/mcp/`, Update 10 tier 2 item 2). Read only, local over stdio,
  through the `mcp` Python SDK 2.x (`MCPServer`, not the 1.x `FastMCP`). Five tools; every
  answer carries `resource_ids` and `fhir`. Reads our read only API (`--api`) or a local export
  (`--export`, written by `scripts/export_records.py`, `make export-records`). `GET /api/creeks`
  is new so the server can list creeks. Stored records now carry the observer's test sitting, so
  the per feature score is structured in FHIR and `get_observer_score` reads it from the record.
  Eight contract tests, including one real run over stdio. `examples/mcp/README.md` has the
  Claude config; `examples/mcp/transcript.md` is one real session from a throwaway database.
- **`make new-city`** (`scripts/new_city.py`, Update 10 tier 2 item 3). A name and coordinates
  give a region pack stub, four nested Locations in FSH under their profile in a Bundle the
  validator checks, a poster with the city's name and two empty photo slots, and the five step
  checklist. Run once for Heraklion as a dry example in English with no claims:
  `docs/cities/heraklion/`. `docs/cities/TIMES.md` records 0.1 seconds for Heraklion and, from
  git, 3 hours 21 minutes for the same four things by hand in Berkeley.
- **The proposal** (`docs/ig_proposal.md`, Update 10 tier 2 item 4) now names three gaps: no
  profile for the person or the trail from an answer to them, a volunteer modelled as a
  Practitioner for want of a better fit, and `SpecimenOah.collection.collector` allowing only a
  PractitionerRole, which made us invent a role for a laboratory. It lists the referral, the
  example result and the Library beside the visit, carries the current validator line (7 files,
  0 errors), and asks for six additions. Its FSH builds inside their guide at b907cf0 in CI.
- **Answer A1, the API behind the Pages origin.** `apps/web/wrangler.jsonc` binds the Worker as
  a service; `apps/web/functions/` hands `/api/*` and `/health` to it; `public/_routes.json`
  keeps the static share cards out of the Function. Built with an empty API origin the policy
  says `connect-src 'self'`. Live on the depth preview, verified with curl; production is
  untouched until `main` deploys with the file. `make deploy-preview` is the one command.
- **Answer A3, first half: the ports and their proof.** `evals/golden_vectors.py` writes
  `worker/golden/*.json` from the Python reference: 97 cases over the follow-up selector, the
  labels, the health card picker, the pin guards and the city functions, the region placement,
  the FHIR emitter, and the hash and rounding helpers. `worker/src/core/*.ts` reproduces every
  one (`cd worker && npm test`), and the TypeScript emitter's Bundles land in
  `fhir/build/instances/` where `make fhir-validate` checks them with the HL7 validator. The
  ports read their tables from `worker/src/content.json`, which Python writes; both files have
  a `--check` that fails `make check` when stale. Nothing on the Worker serves them yet.
- **Answer A3, second half: the judge facing endpoints on the Worker.** `worker/src/check.ts`,
  `city.ts`, `uploads.ts`, `two.ts` and the routes in `index.ts` port the Python API over D1
  and KV: the creek check with its follow ups and rainfall, the record with its FHIR and the
  observer's sitting inside, `/api/city`, `/api/creeks`, the referral and the example, the two
  observer screen, uploads with metadata cut out and a 30 day KV expiry. `make worker-e2e`
  runs it all under `wrangler dev` with a local D1 and KV and a rain stub: 9 sections green.
  Not deployed: production deploys come from `main`; `docs/notes/hosting.md` says how.
- The backup workflow is manual only until the two GitHub secrets exist (Update 10 answer A2).
- `scripts/tests/fixtures/labels_*.csv` are committed. They were untracked, so `make check` was
  green only on the machine that happened to have them.

## What is next on `depth`, in order (Update 10B)

1. Tier 3 of Update 10 (the README in the winning shape, the trust tables, the three Mermaid
   diagrams, `make judge-check`, the scorecard) the day UPDATE_12's numbers exist, per Update 13
   item 6. Until then the README shows no table. Nothing else from Updates 10B, 10C or 13 is left. Tiers 1 and 2 and answers A1, A2 and A3 are done on
   this branch; the pull request stays a draft. Tier 3 waits for its own session after data lock
   on Sep 27; tier 4 waits for the freeze.
2. At merge time, after data lock, in the order in `docs/notes/hosting.md`: the D1 tables and
   the Worker, the study contract and phone tests against production, then the Pages file, then
   the phone tests again. Also append the two pending audit lines from
   `docs/notes/sandbox_library.md`, and run the first real mirror as one tagged batch. Tier 3 waits for its own session after data lock; tier 4 waits for the freeze.

## Traps

- `make check` needs Java 17: `export JAVA17_HOME=/opt/homebrew/opt/openjdk@17`.
- `ruff format --check` runs inside `make lint`, so a docstring that ruff wants to reflow stops
  the whole gate before a single test runs. Run `uv run ruff format .` before `make check`.
- NEXT_PUBLIC_* are inlined at build time. A plain `npm run build` bakes the default API origin.
- Kill anything on port 3100 before measuring: a stale server serves an old build.
- `npm run export` does not fire npm's prebuild hook; the export script runs those steps itself.
- A stored answer is keyed by the form item, a measure by the feature. `content/form.yaml` is the
  one home for that mapping.
- The API test store folder is shared by every test in the process. Count files as a delta.
- New codes go in two places or the emitter test goes red on purpose: `SL_DISPLAYS` in
  `core/fhir_emit.py` and `fhir/fsh/codesystem-second-look.fsh`.
- A visit whose answers ask no follow-up gets no `dry_pipe` question, and `finalize` refuses an
  answer to a question it never asked. Test helpers answer only what the draft asked.
- `audit/log.jsonl` does not exist on either branch yet, and a hash chain cannot be started on
  two branches and merged. The two `sandbox_push` lines from the write back went to a scratch
  file; `docs/notes/sandbox_library.md` lists them for appending to the real chain at merge time.
  Anything on `depth` that would write the audit log should set `AUDIT_LOG_PATH` outside the repo.
- The `mcp` SDK is 2.x: `from mcp.server.mcpserver import MCPServer`; a plain exception inside a
  tool is hidden behind "Error executing tool", so raise `ToolError` for a message an agent may
  read. `mcp.client.Client(server)` connects in memory for tests.
- pytest fixtures are per folder. `apps/mcp/tests/conftest.py` imports the API's `client`
  fixture so the MCP tests can make real records.
- `worker/src/content.json` and `worker/golden/*.json` are written by Python and checked for
  staleness in `make check`. After a change to `content/`, `core/` or the emitter, run
  `uv run python scripts/build_worker_content.py` and `uv run python evals/golden_vectors.py`.
- Python's `round()` rounds an exact tie to even; `toFixed` rounds it up. `pyround.ts` matches
  Python, and a coordinate stored by the Worker must go through it or the two records differ.
- CI runs on pushes to `main` and on pull requests. Pull request #1 is what makes it run for
  `depth`; closing it would stop that. It went green on 2026-09-21 after three CI only fixes:
  the runner needed Playwright's Chromium for design-check, wrangler 4.135 needs Node 22 so the
  e2e step sets it up after the Node 20 web build, and the e2e now runs wrangler's CLI script
  directly with a watchdog, because through npx a kill left a process holding the job's output
  and the step ran silent until the runner's limit.
- The local Workers runtime lags the edge: `wrangler dev` refuses the production compatibility
  date, so the e2e passes `--compatibility-date 2026-08-18` (or `E2E_COMPAT_DATE`). Production
  keeps its date in `worker/wrangler.jsonc`.
- D1 rows written in the same second sort by their random ids; "latest" means `ORDER BY rowid`.
- A Pages wrangler file becomes the project's source of truth for the environment it is deployed
  to. `--branch depth` sets previews only; a `main` deploy with the file would set production, so
  merge it knowingly. `/api/share/*` must stay excluded in `_routes.json` or the share cards 404.
- Playwright specs run as CommonJS: no `import.meta`; use `__dirname` and a dynamic import of a
  file URL to load an ES module under test.
- The region pack's boxes are approximate and hand filled. A wrong box misplaces a precise pin
  onto the wrong reach; the fix is in `content/regions/california-bay-area.yaml`, nowhere else.
