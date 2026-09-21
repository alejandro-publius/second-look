# Handoff: where Second Look stands, 2026-09-21

Two branches, two jobs.

- **`main`, in `~/second-look`.** The launch build. Production deploys come from here only. It is
  waiting on photo picks: open `photos/candidates/*.html`, tick photos, press the download button.
  `make preflight-launch` is the gate, 66 failures, all of them content.
- **`depth`, in the `~/second-look-depth` worktree.** Update 10 and 10B, the full loop. Nothing
  here is deployed to the live link. Merge into `main` only after `make check` and the phone end
  to end tests pass, and never between the `prereg-v1` tag and data lock unless the diff leaves
  the test flow untouched.

## Live

| Thing | Where |
|---|---|
| Site | https://second-look-79t.pages.dev (from `main`) |
| Preview of `depth` | https://depth.second-look-79t.pages.dev, API on the same origin, `make deploy-preview` |
| API | https://second-look-api.thealexschroeder.workers.dev |
| Database | D1 `second-look`, id `aff80e0b-6165-4e53-96f5-ff15716221df` |

## What is done on `depth`

- `docs/DEPTH_MAP.md`: every feature, read out of the repo. 45 built, 3 parked, 6 missing.
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
  `docs/screens/sandbox-library.png` is the screenshot. `scripts/repush_sandbox.py` gained
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

1. Nothing from Update 10B or 10C is left. Tiers 1 and 2 and answers A1, A2 and A3 are done on
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
