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
| API | https://second-look-api.thealexschroeder.workers.dev |
| Database | D1 `second-look`, id `aff80e0b-6165-4e53-96f5-ff15716221df` |

## What is done on `depth`

- `docs/DEPTH_MAP.md`: every feature, read out of the repo. 39 built, 5 parked, 9 missing.
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
- The backup workflow is manual only until the two GitHub secrets exist (Update 10 answer A2).
- `scripts/tests/fixtures/labels_*.csv` are committed. They were untracked, so `make check` was
  green only on the machine that happened to have them.

## What is next on `depth`, in order (Update 10B)

1. Tier 1 item 4: the downstream note. The region pack gains creeks and reaches with a
   `flows_into` field, filled by hand for Strawberry Creek; each creek has a readable slug so the
   link reads `/city?creek=strawberry-creek`; the store keeps its generated ids. The note appears
   only where `flows_into` is set.
2. Tier 2 item 1: mirror the sample record to the sandbox and register a Library entry there,
   with evidence and a screenshot path saved at once.
3. Tier 2 item 2: the MCP server, read only, local over stdio, five tools, contract tests, a
   transcript in `examples/mcp/`.
4. Tier 2 item 3: `make new-city`, run once for Heraklion. Record the two durations.
5. Tier 2 item 4: finish `docs/ig_proposal.md`; the FSH keeps building at the pinned commit.
6. Answer A1: the API behind `/api/*` on the Pages origin. Answer A3: the judge facing endpoints
   on the Worker, proved by golden vectors the Python writes and the TypeScript reproduces.
7. Then stop. Tier 3 waits for its own session after data lock; tier 4 waits for the freeze.

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
