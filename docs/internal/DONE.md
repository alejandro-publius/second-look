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
| D19 | 8 to 10 ADRs in `docs/adr`, each with status, context, decision and consequences | CHECK | | | | `uv run python scripts/done_items.py adrs` |
| D20 | Dependabot for Python, npm (`apps/web` and `worker`) and GitHub Actions | CHECK | | | | `uv run python scripts/done_items.py dependabot` |
| D21 | pre-commit, running ruff and the dash check | CHECK | | | | `uv run python scripts/done_items.py precommit` |
| D22 | Up to 12 topics on GitHub: 8 to 12 | CHECK | | | | `n=$(gh repo view alejandro-publius/second-look --json repositoryTopics --jq '.repositoryTopics \| length') && [ "$n" -ge 8 ] && [ "$n" -le 12 ]` |

## Hardening

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D23 | A second adversarial review, of the finished repo | CHECK | | | | `uv run python scripts/done_items.py review` |
| D24 | Critic rounds in `docs/internal/reviews/`, the newest two reporting nothing above cosmetic | CHECK | | | | `uv run python scripts/done_items.py critics` |
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
| D36 | `make go-public` prepared: its tests pass and its dry run names this repo | CHECK | | | | `repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner) && make -n go-public >/dev/null && uv run python scripts/go_public.py \| grep -qF "gh repo edit $repo --visibility public" && uv run pytest -q scripts/tests/test_go_public.py` |
| D37 | `docs/ALEX_TODO.md` with only human steps | CHECK | | | | `uv run python scripts/done_items.py alex-todo` |

## Dated items

| ID | Item | Kind | Date | Outside cause | Cause test | Command |
|---|---|---|---|---|---|---|
| D38 | Data lock: the audit log records `data_lock` at or after the lock, and its chain holds | DATED | 2026-09-28T01:00:00Z | | | `uv run python scripts/verify_audit.py && uv run python scripts/done_items.py data-lock` |
| D39 | The analysis run once on real data, as a description, after the lock | DATED | 2026-09-28T01:00:00Z | | | `uv run python scripts/done_items.py analysis-once` |
| D40 | `/demo` opens on the live site on Sep 28 | DATED | 2026-09-28T01:00:00Z | | | `make demo-open-check` |
| D41 | The sandbox re-push after the lock, when their name resolves | BLOCKED-IF | 2026-09-28T01:00:00Z | Their sandbox name sandbox.hl7europe.eu does not resolve (NXDOMAIN at their own nameserver since 2026-09-23) | `! python3 -c "import socket; socket.getaddrinfo('sandbox.hl7europe.eu', 443)" 2>/dev/null` | `uv run python scripts/done_items.py sandbox-repush` |

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
| D51 | The panel study launched by Alex (Prolific or similar), by Sep 26 evening: completed sessions from `panel` on the live counts | HUMAN | | | | `curl -fsS https://second-look-79t.pages.dev/api/test/counts \| python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin)['by_source'].get('panel',0) > 0 else 1)"` |
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
