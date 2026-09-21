# Handoff: where Second Look stands, 2026-09-21

Two branches, two jobs.

- **`main`, in `~/second-look`.** The launch build. Production deploys come from here only. It is
  waiting on photo picks: open `photos/candidates/*.html`, tick photos, press the download button.
  `make preflight-launch` is the gate, 66 failures, all of them content.
- **`depth`, in the `~/second-look-depth` worktree.** Update 10, the full loop. Nothing here is
  deployed to the live link. Merge into `main` only after `make check` and the phone end to end
  tests pass, and never between the `prereg-v1` tag and data lock unless the diff leaves the test
  flow untouched.

## Live

| Thing | Where |
|---|---|
| Site | https://second-look-79t.pages.dev (from `main`) |
| API | https://second-look-api.thealexschroeder.workers.dev |
| Database | D1 `second-look`, id `aff80e0b-6165-4e53-96f5-ff15716221df` |

## What is done on `depth`

- `docs/DEPTH_MAP.md`: every feature, read out of the repo. 33 built, 5 parked, 17 missing, and
  the missing ones cluster under one verb, ACT.
- `core/act.py`: findings from visits, what a creek needs, pipes worth testing, the duplicate pin
  guard, the test pin guard, the downstream note. Pure, 21 tests, every guard mutation tested.
- `GET /api/city/{creek_id}` and `/city?creek=` : the analyst's view. No number without its
  Bundle links. An unapproved measure is absent and the page says why.
- A pin within 30 metres of an existing precise spot is offered on the draft response. A coarse
  pin is never compared, because its position is rounded to about a kilometre.
- The backup workflow is manual only until the two GitHub secrets exist (Update 10 answer A2).
- `scripts/tests/fixtures/labels_*.csv` are committed. They were untracked, so `make check` was
  green only on the machine that happened to have them.

## What is next on `depth`, in order

1. Tier 1 item 2: the ServiceRequest referral for a pipe worth testing, and the example lab
   result coming back. Watermarked, tagged as an example, never counted.
2. Tier 1 item 4: the downstream note wired into the record. `core.act.downstream_note` exists
   and is tested; nothing calls it, because the store does not yet say which reach flows into
   which.
3. Tier 2: the sandbox Library entry, the MCP server, `make new-city`, the proposal.
4. Tier 3: the README in the winning shape, `make judge-check`, the diagrams, the scorecard.
5. Tier 4: design stage 2 for `/city` and `/judges`, the Spanish draft, `make readability`.
6. Answer A1: put the API behind `/api/*` on the Pages origin, so the policy can say
   `connect-src 'self'`. Answer A3: port the judge facing endpoints to the Worker, proved by
   golden vectors the Python writes and the TypeScript has to reproduce.

## Traps

- `make check` needs Java 17: `export JAVA17_HOME=/opt/homebrew/opt/openjdk@17`.
- NEXT_PUBLIC_* are inlined at build time. A plain `npm run build` bakes the default API origin.
- Kill anything on port 3100 before measuring: a stale server serves an old build.
- `npm run export` does not fire npm's prebuild hook; the export script runs those steps itself.
- A stored answer is keyed by the form item, a measure by the feature. `content/form.yaml` is the
  one home for that mapping.
