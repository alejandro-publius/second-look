# Definition of done

UPDATE_27 sections 0, 2 and 3 (blocks 25 and 26). The run is finished when `make done-check` ends
with `RED: 0` and only BLOCKED and HUMAN items are left. Written 2026-09-24.

## How to read this file

Every item is one table row, in the order UPDATE_27 lists the work. `scripts/done_check.py` reads
the rows and runs each command from the repo root under bash with pipefail, with a time limit of
120 seconds. A command exits 0 only when the thing is really there; every one of them fails when
the thing is missing. A command that cannot fail (`true`, `|| true`, `|| echo`, `; echo` at the
end, a trailing `&`, an `if` without `else`, `exit 0`, `set +o pipefail`) is refused when the file
is read. Inside a table a pipe is written `\|`; the checker reads it back as `|`.

The kinds:

- **CHECK**: the command must pass now.
- **DATED**: the command must pass once the Date has come. Before that the line prints BLOCKED with
  the date.
- **BLOCKED-IF**: the item waits on something outside the repo. The cause test exits 0 while that
  cause still holds and runs again on every pass; the line then prints BLOCKED with the cause and
  the time it was tested. A Date, when given, is the earliest the item can be done.
- **HUMAN**: only a person can do it. Its command still says whether it was done: PASS when it
  was, HUMAN when it was not. A HUMAN line is never RED.

Never weaken a command to make it pass (UPDATE_27 section 2 item 4). Fix the thing, or mark it
BLOCKED-IF with a cause outside the repo and a cause test.

## What the checks expect

- **Fresh results.** The hardening results in `results/harden/` count only when measured at a
  commit that contains 8cecc38, the tip of `depth` when UPDATE_27's work began (the `commit`
  field), or, for `load_live.json`, finished after that commit's time. An older file measured an
  older README and an older site. axe and Lighthouse must each have measured every page in
  `apps/web/app`, `/t` included; `/share/12` stands for `share/[score]`.
- **Reviews.** `docs/internal/reviews/REVIEW_<nn>.md`, `CRITIC_<nn>.md` and
  `JUDGE_SIM_<nn>_<name>.md`, numbered upward. The newest review and judge simulation name the
  commit they read first in their text, as "commit <sha>". A critic round carries two lines of
  its own, `Commit: <sha>` and `Highest severity: <none, cosmetic, minor, should-fix or major>`.
- **Screens.** Every route in `apps/web/app` and the five screens inside `/t` (consent, warmup,
  lesson, item, score) have a screenshot in `docs/screens` whose file name holds that name.
  Every screenshot there is under 400,000 bytes, and all but the desktop ones share one size: the
  device frame.
- **The README order** is walked top down: the track statement, one sentence, the badges, the
  question "Which creek is healthier?" with the two warm-up photos and a `<details>` block with a
  `<summary>`, a line with three links and the GIF, all above the first section heading; then the
  headings in the order of UPDATE_27 section 3, block 23. Other sections may sit between them.
- **ALEX_TODO.** Numbered steps only for Alex, each with a date or a day on its first line, none
  about work a session or a subagent does, and no more steps than there are HUMAN items below.
- **The voice** is a recording of at least 120 seconds in `~/second-look-media/voice/`, outside
  the repo (`SECOND_LOOK_MEDIA` moves the folder).
- **Devpost.** Its project page link, `https://devpost.com/software/<name>`, goes in
  `docs/devpost.md`. The page counts as ours only when it links the live site, because another
  team's "Second Look" already answers at `devpost.com/software/second-look`. It counts as
  submitted only when its "Submitted to" list links `oneaquahealth-ieee-hackathon.devpost.com`.

## UPDATE_22

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D01 | UPDATE_22 shipped: its report is committed, its ship commit b876a2b is on `main`, and CI passed on that commit | CHECK | | | | `test -f docs/internal/reports/20260924T041834Z.md && grep -q "UPDATE_22 report" docs/internal/reports/20260924T041834Z.md && git merge-base --is-ancestor b876a2b origin/main && gh run view 35954560918 --repo alejandro-publius/second-look --json conclusion,headSha --jq '.conclusion + " " + .headSha' \| grep -q '^success b876a2b'` |

## Block 23: the repo lift

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D02 | Screenshots of every screen from the live site in one device frame, each under 400 KB, in `docs/screens` | CHECK | | | | `uv run python scripts/done_items.py screens` |
| D03 | The GIF of the two-minute test in the README, in the repo, under 3 MB, more than one frame | CHECK | | | | `uv run python scripts/done_items.py gif` |
| D04 | Two lesson photos with their marks in the README | CHECK | | | | `uv run python scripts/done_items.py lesson-marks` |
| D05 | Three Mermaid diagrams in the README (the system map by the five verbs with labelled edges, the FHIR resource graph, the AI gate as a sequence diagram), rendered by `make diagrams` in CI | CHECK | | | | `uv run python scripts/done_items.py diagrams && make diagrams` |
| D06 | The judge-first README in the exact section order of UPDATE_27 section 3 | CHECK | | | | `uv run python scripts/done_items.py readme-order` |
| D07 | Repo description, homepage and topics set on GitHub | CHECK | | | | `gh repo view alejandro-publius/second-look --json description,homepageUrl,repositoryTopics --jq '(.description \| length > 0) and .homepageUrl == "https://second-look-79t.pages.dev" and (.repositoryTopics \| length > 0)' \| grep -qx true` |
| D08 | A 1280 by 640 social preview image in the repo, under 1 MB | CHECK | | | | `uv run python scripts/done_items.py social-image` |

## Block 24: the Tideline layer

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D09 | The gate as the heart of it: a README section in numbered steps, each naming files that exist, `core/gate.py` among them | CHECK | | | | `uv run python scripts/done_items.py gate-steps` |
| D10 | Three properties that follow, each tied to a test that exists | CHECK | | | | `uv run python scripts/done_items.py properties` |
| D11 | Engineering challenges in `WRITEUP.md`, linked from the README, every number in it traced to `results/` | CHECK | | | | `uv run python scripts/done_items.py writeup && uv run python scripts/verify_claims.py --synthetic --file WRITEUP.md` |
| D12 | Security and privacy in the README, pointing at `docs/DATA_HANDLING.md` | CHECK | | | | `uv run python scripts/done_items.py security` |
| D13 | The API table: at least 5 routes, each served by the Worker or the API | CHECK | | | | `uv run python scripts/done_items.py api-table` |
| D14 | The MCP tools table: exactly the tools `apps/mcp/server.py` defines | CHECK | | | | `uv run python scripts/done_items.py mcp-table` |
| D15 | The tech stack | CHECK | | | | `uv run python scripts/done_items.py tech-stack` |
| D16 | Running locally with offline demo data, every `make` target it names real | CHECK | | | | `uv run python scripts/done_items.py run-locally` |
| D17 | The tests paragraph with counts traced to `results/` | CHECK | | | | `uv run python scripts/done_items.py tests-paragraph && uv run python scripts/verify_claims.py --synthetic` |
| D18 | `DEPLOY.md` and a configuration table whose settings a config or code file uses | CHECK | | | | `uv run python scripts/done_items.py deploy-doc` |
| D19 | 8 or more ADRs in `docs/adr` (UPDATE_24 asked 8 to 10; UPDATE_29 adds one), each with status, context, decision and consequences | CHECK | | | | `uv run python scripts/done_items.py adrs` |
| D20 | Dependabot for Python, npm (`apps/web` and `worker`) and GitHub Actions | CHECK | | | | `uv run python scripts/done_items.py dependabot` |
| D21 | pre-commit, running ruff and the dash check | CHECK | | | | `uv run python scripts/done_items.py precommit` |
| D22 | Up to 12 topics on GitHub: 8 to 12 | CHECK | | | | `n=$(gh repo view alejandro-publius/second-look --json repositoryTopics --jq '.repositoryTopics \| length') && [ "$n" -ge 8 ] && [ "$n" -le 12 ]` |

## Hardening

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D23 | A second adversarial review, of the finished repo | CHECK | | | | `uv run python scripts/done_items.py review` |
| D24 | Critic rounds in `docs/internal/reviews/`: the newest two on the same commit, no finding a skeptic confirmed at major or worse, and every confirmed minor fixed or in the README's Known weaknesses, as each round's Resolution says (UPDATE_30 section 2) | CHECK | | | | `uv run python scripts/done_items.py critics` |
| D25 | The six-judge simulation, rerun on the finished repo | CHECK | | | | `uv run python scripts/done_items.py judge-sim` |
| D26 | axe clean on every screen, with an `/accessibility` page that is live | CHECK | | | | `uv run python scripts/done_items.py axe && curl -fsS -o /dev/null https://second-look-79t.pages.dev/accessibility` |
| D27 | Lighthouse on every page: each loads, performance 90 or more, accessibility 95 or more | CHECK | | | | `uv run python scripts/done_items.py lighthouse` |
| D28 | A load test on the live site with no failed session or request | CHECK | | | | `uv run python scripts/done_items.py load` |
| D29 | 90 percent coverage on `core/` | CHECK | | | | `make coverage-core` |
| D30 | No flaky tests over three runs, every suite run each time | CHECK | | | | `uv run python scripts/done_items.py flaky` |
| D31 | Every README command executed | CHECK | | | | `uv run python scripts/done_items.py readme-commands` |
| D32 | A link check with no dead link | CHECK | | | | `uv run python scripts/done_items.py links` |
| D33 | `make readability` | CHECK | | | | `make readability` |

## The submission pack

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D34 | `docs/devpost.md` verified by verify_claims, with claims in it | CHECK | | | | `uv run python scripts/verify_claims.py --file docs/devpost.md \| grep -Eq '^verify-claims: [1-9][0-9]* claim'` |
| D35 | `make submit-check` red only on video_link and repo_public | CHECK | | | | `uv run python scripts/done_items.py submit-pack` |
| D36 | `make go-public` does the day in order (UPDATE_30 8.1): its tests pass, GO=dry maps to --no-flip, its plan names this repo's flip | CHECK | | | | `repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner) && make -n go-public GO=dry \| grep -q -- --no-flip && uv run python scripts/go_public.py \| grep -qF "gh repo edit $repo --visibility public" && uv run pytest -q scripts/tests/test_go_public.py` |
| D37 | `docs/ALEX_TODO.md` with only human steps | CHECK | | | | `uv run python scripts/done_items.py alex-todo` |

## Dated items

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D38 | Data lock: the audit log records `data_lock` at or after the lock, and its chain holds | DATED | 2026-09-28T01:00:00Z | | | `uv run python scripts/verify_audit.py && uv run python scripts/done_items.py data-lock` |
| D39 | The analysis run once on real data, as a description, after the lock | DATED | 2026-09-28T01:00:00Z | | | `uv run python scripts/done_items.py analysis-once` |
| D40 | `/demo` opens on the live site on Sep 28 | DATED | 2026-09-28T01:00:00Z | | | `make demo-open-check` |
| D41 | The sandbox re-push after the lock, when their name resolves | BLOCKED-IF | 2026-09-28T01:00:00Z | Their sandbox name sandbox.hl7europe.eu does not resolve (NXDOMAIN at their own nameserver since 2026-09-23) | `python3 -c $'import socket, sys\ntry:\n    socket.getaddrinfo("sandbox.hl7europe.eu", 443)\nexcept socket.gaierror:\n    sys.exit(0)\nsys.exit(1)' 2>/dev/null` | `uv run python scripts/done_items.py sandbox-repush` |

## Human items

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D42 | The API key: `ANTHROPIC_API_KEY` in `~/second-look-depth/.env` | HUMAN | | | | `grep -Eq '^ANTHROPIC_API_KEY=[^[:space:]]{20,}' "$HOME/second-look-depth/.env"` |
| D43 | The voice recording, by Sep 25, saved in `~/second-look-media/voice/` | HUMAN | | | | `uv run python scripts/done_items.py voice` |
| D44 | The social preview image uploaded in the repo's settings on GitHub | HUMAN | | | | `gh api graphql -f query='query { repository(owner: "alejandro-publius", name: "second-look") { usesCustomOpenGraphImage } }' --jq .data.repository.usesCustomOpenGraphImage \| grep -qx true` |
| D45 | Devpost: the project page filled from `docs/devpost.md`, its link put in that file | HUMAN | | | | `uv run python scripts/done_items.py devpost-page` |
| D46 | The video uploaded, by Sep 29, its link in the README and in `docs/devpost.md` | HUMAN | | | | `uv run python scripts/done_items.py video-link` |
| D47 | Go public on Sep 30: `make go-public GO=yes` on `main` | HUMAN | | | | `gh repo view alejandro-publius/second-look --json visibility --jq .visibility \| grep -qx PUBLIC` |
| D48 | Submit on Devpost by 18:00 on Sep 30 | HUMAN | | | | `uv run python scripts/done_items.py devpost-submitted` |

## UPDATE_29: undeniable (last, in file order)

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D49 | The panel study, software side: `?src=panel` shows a fixed completion code on the end screen, the consent sentence shows for that source only, every query parameter but `src` is stripped before anything is stored, `make panel-status` works, `docs/internal/PANEL_STUDY.md` has every part, and a deviation is logged | CHECK | | | | `uv run python scripts/done_items.py panel-prep` |
| D50 | The analysis handles the panel source label and the lock as the tagged plan says, on synthetic data | CHECK | | | | `uv run python scripts/done_items.py panel-analysis` |
| D51 | The panel study launched by a team member (Prolific or similar), by Sep 26 evening: completed sessions from `panel` on the live counts | HUMAN | | | | `curl -fsS https://second-look-79t.pages.dev/api/test/counts \| python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin)['by_source'].get('panel',0) > 0 else 1)"` |
| D52 | After the lock: the pre-registered analysis run once and its result in the README's human row and numbers table | DATED | 2026-09-28T01:00:00Z | | | `uv run python scripts/done_items.py human-row` |
| D53 | Contributed back: a pull request to hl7-eu/oah with the citizen example and the proposal, two issues (the `morophology` spelling, the `SpecimenOah` collector), the sandbox DNS issue, each linked by number in the README | CHECK | | | | `uv run python scripts/done_items.py contributed-back` |
| D54 | OpenTimestamps proofs for the `prereg-v1` tag object and `docs/analysis_plan.md` committed, and the audit chain head anchored daily | CHECK | | | | `uv run python scripts/done_items.py ots` |
| D55 | `/verify` shows a record's receipt, chain position and OpenTimestamps status, and says what OpenTimestamps is; both proofs in the trust table with their commands | CHECK | | | | `uv run python scripts/done_items.py verify-page` |
| D56 | `make reproduce` regrades every number in `results/` from committed raw responses and seeds, no network and no key, and is in `make judge-check` and the README's Evals | CHECK | | | | `uv run python scripts/done_items.py reproduce` |
| D57 | Mutation testing on the gate, the follow-up selector, scoring and the FHIR emitter: score at or above 85 percent, in `results/` and the README's numbers | CHECK | | | | `uv run python scripts/done_items.py mutation` |
| D58 | Lighthouse on the landing page: performance, accessibility, best practices and SEO all 95 or above on the throttled profile, in `results/` | CHECK | | | | `uv run python scripts/done_items.py lighthouse-landing` |
| D59 | `docs/MODEL_CARD.md`, linked from the track statement's line in the README | CHECK | | | | `uv run python scripts/done_items.py model-card` |
| D60 | `docs/THREAT_MODEL.md`: assets, four kinds of attacker, what each could do, what stops it, with tests that exist | CHECK | | | | `uv run python scripts/done_items.py threat-model` |
| D61 | `docs/REPORT.pdf`, about six pages, built by pandoc from the README and `results/`, linked from the README and `docs/devpost.md` | CHECK | | | | `uv run python scripts/done_items.py report-pdf` |
| D62 | `docs/DATA_CARD.md` for the photo and footage sets | CHECK | | | | `uv run python scripts/done_items.py data-card` |
| D63 | A second labeller (optional): if a second label file exists, kappa per feature is reported | HUMAN | | | | `uv run python scripts/done_items.py second-labeller` |
| D64 | iNaturalist context line on the record page and `/city`, cached in D1 by a daily Mac job, attributed, with an ADR, and degrading to "no recent sightings on record" | CHECK | | | | `uv run python scripts/done_items.py inaturalist` |
| D65 | The loop again over everything new: the adversarial review, the six-judge simulation and the two clean critic rounds each read a commit that holds every UPDATE_29 file | CHECK | | | | `uv run python scripts/done_items.py rerun-after-update` |
| D66 | The Bay Area invasive list approved for the team (UPDATE_29 section 8; approved 2026-09-25, UPDATE_30 section 3), so the iNaturalist line can name sightings | CHECK | | | | `uv run python scripts/done_items.py invasive-list` |

## UPDATE_30: the final week

Items that run a browser prove it through CI: the spec is on `main` and the newest check run on `main`, whose `make e2e` runs every spec, passed.

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D67 | A first visit downloads no more than 3 MB in the background (UPDATE_30 1.1): the measured number is under the budget, at a commit of this repo, with the offline copies committed; the precache holds only the offline pages and one phone-size copy per photo of the test | CHECK | | | | `uv run pytest -q scripts/tests/test_precache_budget.py scripts/tests/test_derive_photos.py && grep -q "list.fallbacks" apps/web/public/sw.js` |
| D68 | After one visit a started test runs offline, and the budget test runs in CI: offline-budget.spec.ts is on main and the newest check run on main passed | CHECK | | | | `git fetch -q origin main && git grep -q "all 16 photos offline" origin/main -- apps/web/tests/offline-budget.spec.ts && gh run list --repo alejandro-publius/second-look --branch main --workflow check --limit 1 --json conclusion,status --jq '.[0].status + " " + .[0].conclusion' \| grep -qx "completed success"` |
| D69 | A walk's answers survive Back, a reload and a closed tab, kept in IndexedDB beside the offline queue, keyed by walk id (UPDATE_30 1.2) | CHECK | | | | `grep -q "four answers survive Back and a reload" apps/web/tests/walk-store.spec.ts && grep -q 'createObjectStore(WALKS, { keyPath: "walk_id" })' apps/web/lib/offline.ts && grep -q "setStage(resumeStage(walk, saved))" apps/web/components/WalkFlow.tsx` |
| D70 | A finished walk's demo record is stored in its own table by both servers, guarded, never counted or mirrored, deleted after 30 days (UPDATE_30 1.3) | CHECK | | | | `uv run pytest -q apps/api/tests/test_walk_store.py core/tests/test_walks.py && uv run python evals/golden_vectors.py --check && grep -q "CREATE TABLE IF NOT EXISTS walk_record" worker/schema.sql` |
| D71 | The walk's record link opens in a fresh browser, on /spot?id= and on /city under the demo creek, and the spec runs in CI on main | CHECK | | | | `git fetch -q origin main && git grep -q "record link opens in a fresh browser" origin/main -- apps/web/tests/walk-store.spec.ts && gh run list --repo alejandro-publius/second-look --branch main --workflow check --limit 1 --json conclusion,status --jq '.[0].status + " " + .[0].conclusion' \| grep -qx "completed success"` |
| D72 | No walk page or README line says a walk is never stored | CHECK | | | | `uv run python -c "import json,sys; d=json.load(open('content/locales/en.json')); sys.exit(1 if [k for k,v in d.items() if k.startswith(('walk.','city.walk','judges.record')) and any(p in v.lower() for p in ('never stored','stays on this phone','on this phone only','never sent to anyone'))] else 0)" && ! grep -n -e "never stored or counted" -e "made on the phone and never stored" -e "on the phone, never sent" README.md` |
| D73 | The deployed Worker answers the walk record route | CHECK | | | | `curl -s https://second-look-79t.pages.dev/api/walk/walk-0000000000000000 \| grep -q "no stored walk record"` |
| D74 | Bare /city lists every region pack with its creeks and each creek link opens that creek, also after Back (UPDATE_30 1.4); the spec runs in CI on main and the live read-only check taps each creek | CHECK | | | | `git fetch -q origin main && git grep -q "each creek link shows that creek" origin/main -- apps/web/tests/city-picker.spec.ts && grep -q "for (const creek of picks)" apps/web/scripts/live-readonly.mjs && gh run list --repo alejandro-publius/second-look --branch main --workflow check --limit 1 --json conclusion,status --jq '.[0].status + " " + .[0].conclusion' \| grep -qx "completed success"` |
| D75 | make judge-check serves its web step on 3100 or a free port it names and frees after, and two in one checkout take turns (UPDATE_30 1.5) | CHECK | | | | `uv run pytest -q scripts/tests/test_judge_check_port.py` |
| D76 | make lock-analysis: backup, export, the one tagged analysis, the README human row, make check, commit, deploy, judge mode, an atomic push and a status line; tested end to end on a copy of a database, refusing before the lock by the real clock, undone on any failure (UPDATE_30 5.1) | CHECK | | | | `uv run pytest -q scripts/tests/test_lock_analysis.py scripts/tests/test_study_export.py` |
| D77 | Nothing would stop the lock job on this Mac: its checkout (~/second-look-depth, or JOBS_ROOT) clean on depth, tools, logins, the QA key, a good deploy recorded with its files | CHECK | | | | `test -f results/lock_analysis.json \|\| make -C "${JOBS_ROOT:-$HOME/second-look-depth}" lock-analysis-ready` |
| D78 | Every Mac job, the lock included, installed from ~/second-look-depth and loaded (UPDATE_30 7.4) | CHECK | | | | `uv run python scripts/mac_jobs.py check-installed` |
| D79 | The lock job ran after the lock and its record is on main | DATED | 2026-09-28T02:30:00Z | | | `git fetch -q origin main && git cat-file -e origin/main:results/lock_analysis.json && uv run python scripts/done_items.py human-row` |
| D80 | make panel-status prints by source and arm with the rule of 20, and the status issue shows the counts (UPDATE_30 5.2) | CHECK | | | | `make panel-status \| grep -Eq "20 (or more )?completed sessions" && gh issue view 4 --repo alejandro-publius/second-look --json body --jq .body \| grep -q "panel-counts"` |
| D81 | The daily sandbox retry, both outcomes tested (UPDATE_30 6.1) | CHECK | | | | `uv run pytest -q scripts/tests/test_watch_jobs.py -k "resolve or failed_push or forbidden"` |
| D82 | The hl7-eu/oah watch: new maintainer comments go to the status issue and hl7.log, never a reply (UPDATE_30 6.2) | CHECK | | | | `uv run pytest -q scripts/tests/test_watch_jobs.py -k "maintainer or review or gh_that"` |
| D83 | Uptime every 10 minutes: two failures in a row, one comment per outage, a notification (UPDATE_30 7.1) | CHECK | | | | `uv run pytest -q scripts/tests/test_watch_jobs.py -k "wrong_address or recovery or working_page"` |
| D84 | make rollback: a dry run by default, ROLLBACK=yes acts, every deploy recorded (UPDATE_30 7.2) | CHECK | | | | `uv run pytest -q scripts/tests/test_deploy_rollback.py` |
| D85 | What is live is a recorded good deploy with its files kept | CHECK | | | | `uv run python scripts/deploy_record.py check-live` |
| D86 | docs/internal/MAC_JOBS.md lists every job, its time, script, log and ran-today command (UPDATE_30 7.4) | CHECK | | | | `uv run pytest -q scripts/tests/test_mac_jobs.py` |
| D87 | The Mac stays plugged in and awake through Oct 15 (UPDATE_30 7.4) | HUMAN | | | | `pmset -g batt \| grep -q "'AC Power'" && pmset -g custom \| awk '/^AC Power/{a=1} a && $1=="sleep"{found=1; ok=($2==0)} END{exit !(found && ok)}'` |
| D88 | docs/JUDGE_DAY.md: the 45 second and 10 minute paths, with the fallback while their sandbox is down (UPDATE_30 7.3) | CHECK | | | | `grep -q "## In 45 seconds" docs/JUDGE_DAY.md && grep -q "## In 10 minutes" docs/JUDGE_DAY.md && grep -q "## If their sandbox is still down" docs/JUDGE_DAY.md` |
| D89 | The ethics step in the panel study doc says what the panel asks and what is true, in one paragraph (UPDATE_30 5.3) | CHECK | | | | `grep -q "The ethics question, in one minute" docs/internal/PANEL_STUDY.md` |
| D90 | A go-public dry run recorded in `results/go_public_dryrun.json`: every step before the flip ran, each failure one it explains | CHECK | | | | `uv run pytest -q scripts/tests/test_go_public.py -k recorded_dry_run` |
| D91 | submit-check holds the Devpost text to the form (UPDATE_30 8.2) | CHECK | | | | `test "$(uv run python scripts/submit_check.py \| grep -cE '^PASS  devpost_(track_statement\|fields\|numbers\|report\|team)\b')" = 5` |
| D92 | `docs/SUBMISSION_DAY.md`: Sep 30 in order with times, commands and checks, Monday's dry run, the any-window sentence | CHECK | | | | `grep -q 'can be run from any Claude Code window on the Mac' docs/SUBMISSION_DAY.md && grep -q '^## Mon Sep 28' docs/SUBMISSION_DAY.md && grep -q '^## Wed Sep 30' docs/SUBMISSION_DAY.md && grep -q 'docs/REPORT.pdf' docs/SUBMISSION_DAY.md` |
| D93 | `CHANGELOG.md` names every day with commits from Sep 16 to yesterday; its v1.0 section is the release notes | CHECK | | | | `uv run python -c "from pathlib import Path; from scripts import go_public as g; s = g.step_changelog(g.Run(root=Path.cwd())); print(s.line()); raise SystemExit(s.failed)"` |
| D94 | After the flip: the v1.0 tag and its GitHub release, notes from `CHANGELOG.md` (UPDATE_30 8.4) | HUMAN | | | | `gh release view v1.0 --repo alejandro-publius/second-look --json tagName --jq .tagName \| grep -qx v1.0` |
| D95 | The captions-only final cut exists: under 4:00, 1920 by 1080, captions from the current script burned in, every footage credit, the CC BY-SA end card with the live link, silence | CHECK | | | | `uv run pytest -q scripts/tests/test_video_final.py && test -s "$HOME/second-look-media/final/second-look-final.mp4" && ffprobe -v error -select_streams v:0 -show_entries stream=width,height:format=duration -of csv=p=0 "$HOME/second-look-media/final/second-look-final.mp4" \| tr '\n' ',' \| awk -F, '{exit !($1==1920 && $2==1080 && $3>=180 && $3<240)}'` |
| D96 | A voice file in `~/second-look-media/voice/` is laid over the cut, per beat or whole, with the captions kept as subtitles and an .srt; proved on a generated tone | CHECK | | | | `command -v ffmpeg && uv run pytest -q scripts/tests/test_video_final.py -k "tiny_cut or voice or marks or quiet"` |
| D97 | `docs/video/README.md` documents `make video-final` without and with the voice, and `make video-frames` | CHECK | | | | `grep -q "make video-final" docs/video/README.md && grep -q "voice_beats.txt" docs/video/README.md && grep -q "^video-final:" Makefile && grep -q "^video-frames:" Makefile` |
| D98 | `docs/video/UPLOAD.md`: title, description with every credit and the CC BY-SA line, tags, thumbnail, unlisted upload steps, the Devpost paste | CHECK | | | | `uv run pytest -q scripts/tests/test_video_final.py -k "upload or thumbnail" && test -s "$HOME/second-look-media/final/thumbnail.png"` |
| D99 | The captions only cut fixes the Sep 25 frames review: no restarts, clips from the deployed commit, live curl address, link on screen, 90% caption box, beat 11 left out while their sandbox is down, 3:45 | CHECK | | | | `uv run pytest -q scripts/tests/test_video_final.py scripts/tests/test_video_words.py scripts/tests/test_video_beats.py` |
| D100 | final_cut.json was built from the current shot list and names ~/second-look-media/screens | CHECK | | | | `uv run python -c "import json; d=json.load(open('docs/video/final_cut.json')); assert d['screens_folder']=='~/second-look-media/screens' and d['length_s']<240 and d['left_out']"` |

## UPDATE_31: the assisted second look

Part 2 measures whether the checker's one question makes a person more accurate. Items that run a browser prove it through CI, as in the UPDATE_30 section.

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D120 | UPDATE_31 is saved | CHECK | | | | `test -f docs/internal/updates/UPDATE_31.md` |
| D121 | Plan v2 in the plan's usual items: the eight items and their gold labels frozen, the question wording part 1's, the flag rule, the exclusions, the lock, and a planning note that quotes `results/power_v2.json` (UPDATE_31 2.1, 1) | CHECK | | | | `grep -q "a01 artificial_bank ph-p2-01 present" docs/analysis_plan_v2.md && grep -q "2026-09-28T01:00:00Z" docs/analysis_plan_v2.md && uv run pytest -q evals/tests/test_power_v2.py` |
| D122 | `prereg-v2` tagged before any part 2 session, its SHA-256 in docs/notes/plan_hash.md, an audit entry and an OpenTimestamps proof (UPDATE_31 2.1) | CHECK | | | | `git rev-parse -q --verify refs/tags/prereg-v2 >/dev/null && grep -q "prereg-v2" docs/notes/plan_hash.md && grep -q "$(shasum -a 256 docs/analysis_plan_v2.md \| cut -d' ' -f1)" docs/notes/plan_hash.md && test -f proofs/prereg-v2.tag.ots && uv run python scripts/verify_audit.py` |
| D123 | Eight part 2 photos, two per feature, one present and one absent, never shown in a lesson, a practice card or the test, each with a manifest row and a gold label (UPDATE_31 1) | CHECK | | | | `uv run pytest -q evals/tests/test_assist_flags.py -k part2_items && uv run python scripts/check_manifest.py` |
| D124 | The flags are precomputed from the models' stored answers and the committed pass table, stamped real, and a feature the model did not pass never produces one (UPDATE_31 2.2) | CHECK | | | | `uv run python evals/assist_flags.py --check && uv run pytest -q evals/tests/test_assist_flags.py && uv run python -c "import json,sys; sys.exit(0 if json.load(open('results/assist_flags.json'))['real'] is True else 1)"` |
| D125 | Whatever the flags contain, the stored final answer is the person's choice and a flag never changes an answer by itself; the Worker's port agrees with Python on every golden case (UPDATE_31 3) | CHECK | | | | `uv run pytest -q core/tests/test_assist.py && uv run python evals/golden_vectors.py --check` |
| D126 | The Worker's part 2: the offer refuses a sitting before its score screen, randomizes once per part 1 sitting in blocks of 4 per part 1 arm, answers each first answer only with whether to ask, stores Keep and Change, resends, resumes and exports; the flags never leave it (UPDATE_31 2.3) | CHECK | | | | `grep -q "part 2 cannot start before part 1's score screen" worker/test/part2_e2e.mjs && uv run python scripts/seed_part2_arms.py --check && ! grep -q "part2_flags\|points_to" apps/web/generated/content.json` |
| D127 | /t2 in the browser: both arms, Keep and Change, resume, the panel's code, and part 2 cannot be reached before part 1's score screen; the spec is on main and the newest check run on main passed (UPDATE_31 2.3, 3) | CHECK | | | | `git fetch -q origin main && git grep -q "part 2 cannot be reached before part 1's score screen" origin/main -- apps/web/tests/part2.spec.ts && gh run list --repo alejandro-publius/second-look --branch main --workflow check --limit 1 --json conclusion,status --jq '.[0].conclusion' \| grep -q success` |
| D128 | Part 1's score screen offers part 2 in one line, and that change is logged as a deviation (UPDATE_31 2.3) | CHECK | | | | `grep -q "<Part2Offer" apps/web/components/TestFlow.tsx && grep -q "score screen offers part 2 (UPDATE_31" docs/deviations.md` |
| D129 | The part 2 analysis, tested before the tag on three synthetic scenarios, refuses real data before the lock, without the tag and with a changed plan (UPDATE_31 2.4) | CHECK | | | | `uv run pytest -q evals/tests/test_assist_analysis.py` |
| D130 | The lock job runs the part 2 analysis right after part 1's and fills the README's second human row, or the sentence that too few finished part 2 (UPDATE_31 2.5) | CHECK | | | | `uv run pytest -q scripts/tests/test_lock_analysis.py -k part2` |
| D131 | The panel study doc: about 8 minutes, the payment raised to match, the optional second block in the description, the same code at the end of part 2 and of part 1 (UPDATE_31 2.6) | CHECK | | | | `grep -q "about 8 minutes" docs/internal/PANEL_STUDY.md && grep -q "second look" docs/internal/PANEL_STUDY.md && grep -q "end of part 2" docs/internal/PANEL_STUDY.md` |
| D132 | make panel-status shows part 2 by arm (UPDATE_31 2.7) | CHECK | | | | `uv run pytest -q scripts/tests/test_watch_jobs.py -k part2 && make panel-status \| grep -q "Part 2 by arm"` |
| D133 | The README describes part 2 and its tag under Evals, and its first line says the AI's help is measured, not assumed (UPDATE_31 2.8) | CHECK | | | | `grep -q "prereg-v2" README.md && head -1 README.md \| grep -q "measured, not assumed"` |
| D134 | /judges has "Assisted second look, try it", which opens part 2's judge mode; the spec is on main (UPDATE_31 2.9) | CHECK | | | | `grep -q "<JudgesAssistDoor" apps/web/app/judges/page.tsx && git fetch -q origin main && git grep -q "assisted second look door" origin/main -- apps/web/tests/judges.spec.ts` |
| D135 | Production answers part 2's counts, and the live Worker holds the part 2 tables and slots | CHECK | | | | `curl -s https://second-look-79t.pages.dev/api/t2/counts \| grep -q '"by_arm"'` |
| D136 | The phone test of both part 2 arms against production with the QA key, a Change and a Keep in the assisted arm, recorded (UPDATE_31 3) | CHECK | | | | `uv run python -c "import json,sys; d=json.load(open('results/part2_live_check.json')); sys.exit(0 if d['ok'] and set(d['arms'])=={'assisted','unassisted'} and {'keep','change'}<=set(d['choices']) else 1)"` |
| D137 | Part 2's judge mode opens at the lock on production | DATED | 2026-09-28T01:30:00Z | | | `curl -s -X POST -H 'content-type: application/json' -d '{"item_id":"a01","answer":"yes"}' https://second-look-79t.pages.dev/api/t2/demo \| grep -q '"correct"'` |
| D138 | The lock job ran the part 2 analysis once and its result is on main | DATED | 2026-09-28T02:30:00Z | | | `git fetch -q origin main && git ls-tree --name-only origin/main results/ \| grep -Eq "^results/assist_[0-9]{8}\.json$"` |

## UPDATE_32: the weekend run

The creek check in the official app's own words and languages, the kept rating in its record, walk clips that seek, and the Devpost pictures.

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D140 | UPDATE_32 is saved as the newest update | CHECK | | | | `test -f docs/internal/updates/UPDATE_32.md && ls docs/internal/updates/ \| sort -V \| tail -1 \| grep -q UPDATE_32` |
| D141 | Every creek check item quotes the official app's public bundle, marked verified with its source, the bundle recorded by URL, date and SHA-256 and never committed (UPDATE_32 1) | CHECK | | | | `uv run pytest -q scripts/tests/test_app_strings.py && grep -q "SHA-256" docs/notes/app_strings.md` |
| D142 | The app's bundle, fetched again today, still says every string the creek check quotes (UPDATE_32 1.4; needs the network) | CHECK | | | | `make app-strings-check` |

