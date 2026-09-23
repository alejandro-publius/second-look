# Link check 00

Checked 2026-09-23T05:02:20Z at commit 5474757 by `uv run python scripts/harden_links.py`, over README.md and every tracked Markdown file under docs/ (66 files). Nothing was fixed. Raw rows: `results/harden/links.json`.

Relative links are resolved from the file that holds them and their #anchors are checked against the target's headings the way GitHub makes them. Paths in backticks are resolved from the repo root. Each web address got one GET with redirects followed. A site that answers 401, 403, 405, 429 or 999 to a script is listed as blocked, not dead: open it by hand. A path that git ignores (build output, local data) is listed as ignored, not dead. api.enora-oah.eu and the Resilience Map API were never called (hard rule 9); the HL7 sandbox got at most one GET a second and 50 in all (hard rule 10).

## Counts

| Kind | ok | dead | blocked | private | ignored | skipped |
|---|---|---|---|---|---|---|
| relative | 0 | 0 | 0 | 0 | 0 | 0 |
| backtick | 681 | 85 | 0 | 0 | 20 | 0 |
| url | 185 | 47 | 1 | 5 | 0 | 32 |

## Dead, in the README and product docs

| File and line | Kind | Link | What happened |
|---|---|---|---|
| README.md:66 | backtick | results/key_agreement.json | results/key_agreement.json does not exist |
| docs/CONTRACTS.md:80 | backtick | results/key_agreement.json | results/key_agreement.json does not exist |
| docs/HANDOFF_NEXT.md:19 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/REAL_VS_SYNTHETIC.md:13 | backtick | photos/benchmark/ | photos/benchmark does not exist |
| docs/devpost.md:42 | backtick | docs/notes/devpost_fields.md | docs/notes/devpost_fields.md does not exist |
| docs/notes/hosting.md:22 | backtick | scripts/build-headers.mjs | scripts/build-headers.mjs does not exist |
| docs/notes/hosting.md:74 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/notes/p2_validator_run.md:201 | backtick | docs/ig_gap_report.md | docs/ig_gap_report.md does not exist |
| docs/notes/sandbox_library.md:90 | url (in code) | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | 404 |
| docs/notes/sources.md:17 | url | https://www.cal-ipc.org/plants/profile/tradescantia-fluminensis-profile/ | 404 |

## Dead, in docs/internal (working notes)

| File and line | Kind | Link | What happened |
|---|---|---|---|
| docs/internal/DEPTH_MAP.md:90 | backtick | docs/JUDGE_SCORECARD.md | docs/JUDGE_SCORECARD.md does not exist |
| docs/internal/DEPTH_MAP.md:90 | backtick | docs/ACCEPTANCE.md | docs/ACCEPTANCE.md does not exist |
| docs/internal/KILL_TESTS.md:14 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/KILL_TESTS.md:16 | backtick | photos/probe/ | photos/probe does not exist |
| docs/internal/MASTER_BRIEF.md:7 | backtick | docs/MASTER_BRIEF.md | docs/MASTER_BRIEF.md does not exist |
| docs/internal/MASTER_BRIEF.md:7 | backtick | fhir/citizen_followercity_spike.fsh | fhir/citizen_followercity_spike.fsh does not exist |
| docs/internal/MASTER_BRIEF.md:133 | backtick | results/key_agreement.json | results/key_agreement.json does not exist |
| docs/internal/MASTER_BRIEF.md:233 | backtick | docs/notes/their_image_model.md | docs/notes/their_image_model.md does not exist |
| docs/internal/alex_today.md:23 | backtick | docs/team_pack.md | docs/team_pack.md does not exist |
| docs/internal/alex_today.md:23 | backtick | docs/notes/app_wording.md | docs/notes/app_wording.md does not exist |
| docs/internal/alex_today.md:32 | backtick | docs/KILL_TESTS.md | docs/KILL_TESTS.md does not exist |
| docs/internal/alex_today.md:51 | backtick | docs/notes/devpost_fields.md | docs/notes/devpost_fields.md does not exist |
| docs/internal/alex_today.md:52 | backtick | docs/notes/slack.md | docs/notes/slack.md does not exist |
| docs/internal/alex_today.md:53 | backtick | docs/notes/their_image_model.md | docs/notes/their_image_model.md does not exist |
| docs/internal/alex_today.md:58 | backtick | docs/recruiting_messages.md | docs/recruiting_messages.md does not exist |
| docs/internal/reports/20260921T043754Z.md:9 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reports/20260921T061626Z.md:47 | backtick | docs/DEPTH_MAP.md | docs/DEPTH_MAP.md does not exist |
| docs/internal/reviews/DESIGN_REVIEW_01.md:6 | backtick | docs/updates/UPDATE_06.md | docs/updates/UPDATE_06.md does not exist |
| docs/internal/reviews/JUDGE_SIM_00_before.md:58 | url | https://second-look-79t.pages.dev/city?creek=strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:58 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:58 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:58 | url | https://second-look-api.thealexschroeder.workers.dev/api/two | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:58 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/validation | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:80 | url | https://second-look-79t.pages.dev/city?creek=strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:80 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:93 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-79t.pages.dev/city?creek=strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-79t.pages.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/two | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/validation | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:124 | url | https://second-look-79t.pages.dev/city?creek=strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:124 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:124 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:124 | url | https://second-look-api.thealexschroeder.workers.dev/api/two | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:124 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/validation | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-79t.pages.dev/city?creek=strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-79t.pages.dev/city | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-79t.pages.dev/_next/static/chunks/*.js | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/two | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/validation | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/health | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/city/strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/ | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/city?creek=strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/city | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/city/strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/api/health | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/nonexistent-page-xyz | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-api.thealexschroeder.workers.dev/api/two | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/validation | 404 |
| docs/internal/reviews/REVIEW_01.md:7 | backtick | docs/BUILD_LOG.md | docs/BUILD_LOG.md does not exist |
| docs/internal/reviews/REVIEW_01.md:684 | backtick | results/placeholder_hashes.json | results/placeholder_hashes.json does not exist |
| docs/internal/updates/UPDATE_02.md:8 | backtick | docs/updates/UPDATE_02.md | docs/updates/UPDATE_02.md does not exist |
| docs/internal/updates/UPDATE_02.md:8 | backtick | docs/MASTER_BRIEF.md | docs/MASTER_BRIEF.md does not exist |
| docs/internal/updates/UPDATE_02.md:117 | backtick | docs/notes/devpost_fields.md | docs/notes/devpost_fields.md does not exist |
| docs/internal/updates/UPDATE_02.md:128 | backtick | docs/notes/slack.md | docs/notes/slack.md does not exist |
| docs/internal/updates/UPDATE_02.md:148 | backtick | docs/notes/slack.md | docs/notes/slack.md does not exist |
| docs/internal/updates/UPDATE_02.md:150 | backtick | docs/notes/devpost_fields.md | docs/notes/devpost_fields.md does not exist |
| docs/internal/updates/UPDATE_02.md:151 | backtick | docs/notes/their_image_model.md | docs/notes/their_image_model.md does not exist |
| docs/internal/updates/UPDATE_03.md:17 | backtick | docs/ig_gap_report.md | docs/ig_gap_report.md does not exist |
| docs/internal/updates/UPDATE_03.md:20 | backtick | photos/probe/ | photos/probe does not exist |
| docs/internal/updates/UPDATE_03.md:48 | backtick | docs/ig_gap_report.md | docs/ig_gap_report.md does not exist |
| docs/internal/updates/UPDATE_04.md:9 | backtick | docs/updates/UPDATE_04.md | docs/updates/UPDATE_04.md does not exist |
| docs/internal/updates/UPDATE_04.md:13 | backtick | docs/BUILD_LOG.md | docs/BUILD_LOG.md does not exist |
| docs/internal/updates/UPDATE_04.md:26 | backtick | docs/KILL_TESTS.md | docs/KILL_TESTS.md does not exist |
| docs/internal/updates/UPDATE_04.md:44 | backtick | docs/ig_gap_report.md | docs/ig_gap_report.md does not exist |
| docs/internal/updates/UPDATE_04.md:47 | backtick | docs/BUILD_LOG.md | docs/BUILD_LOG.md does not exist |
| docs/internal/updates/UPDATE_04.md:129 | backtick | docs/reviews/REVIEW_01.md | docs/reviews/REVIEW_01.md does not exist |
| docs/internal/updates/UPDATE_04.md:148 | backtick | docs/rachel_pack.md | docs/rachel_pack.md does not exist |
| docs/internal/updates/UPDATE_04.md:149 | backtick | docs/alex_today.md | docs/alex_today.md does not exist |
| docs/internal/updates/UPDATE_04.md:150 | backtick | docs/recruiting_messages.md | docs/recruiting_messages.md does not exist |
| docs/internal/updates/UPDATE_06.md:9 | backtick | docs/updates/UPDATE_06.md | docs/updates/UPDATE_06.md does not exist |
| docs/internal/updates/UPDATE_06.md:18 | backtick | docs/CONTEXT_LEDGER.md | docs/CONTEXT_LEDGER.md does not exist |
| docs/internal/updates/UPDATE_06.md:86 | backtick | docs/reviews/VOICEOVER.md | docs/reviews/VOICEOVER.md does not exist |
| docs/internal/updates/UPDATE_06.md:112 | backtick | docs/reviews/DESIGN_REVIEW_01.md | docs/reviews/DESIGN_REVIEW_01.md does not exist |
| docs/internal/updates/UPDATE_07.md:5 | backtick | docs/updates/UPDATE_07.md | docs/updates/UPDATE_07.md does not exist |
| docs/internal/updates/UPDATE_07.md:9 | backtick | docs/updates/UPDATE_06.md | docs/updates/UPDATE_06.md does not exist |
| docs/internal/updates/UPDATE_07.md:31 | backtick | docs/KILL_TESTS.md | docs/KILL_TESTS.md does not exist |
| docs/internal/updates/UPDATE_07.md:31 | backtick | docs/updates/UPDATE_03.md | docs/updates/UPDATE_03.md does not exist |
| docs/internal/updates/UPDATE_07.md:35 | backtick | docs/KILL_TESTS.md | docs/KILL_TESTS.md does not exist |
| docs/internal/updates/UPDATE_07.md:48 | backtick | docs/ig_gap_report.md | docs/ig_gap_report.md does not exist |
| docs/internal/updates/UPDATE_07.md:51 | backtick | photos/probe/ | photos/probe does not exist |
| docs/internal/updates/UPDATE_07.md:79 | backtick | docs/ig_gap_report.md | docs/ig_gap_report.md does not exist |
| docs/internal/updates/UPDATE_09.md:5 | backtick | docs/updates/UPDATE_09.md | docs/updates/UPDATE_09.md does not exist |
| docs/internal/updates/UPDATE_09.md:16 | backtick | docs/rachel_pack.md | docs/rachel_pack.md does not exist |
| docs/internal/updates/UPDATE_09.md:16 | backtick | docs/team_pack.md | docs/team_pack.md does not exist |
| docs/internal/updates/UPDATE_09.md:44 | backtick | docs/KILL_TESTS.md | docs/KILL_TESTS.md does not exist |
| docs/internal/updates/UPDATE_10.md:14 | backtick | docs/updates/UPDATE_10.md | docs/updates/UPDATE_10.md does not exist |
| docs/internal/updates/UPDATE_10.md:47 | backtick | docs/DEPTH_MAP.md | docs/DEPTH_MAP.md does not exist |
| docs/internal/updates/UPDATE_10.md:83 | backtick | docs/JUDGE_SCORECARD.md | docs/JUDGE_SCORECARD.md does not exist |
| docs/internal/updates/UPDATE_10.md:83 | backtick | docs/ACCEPTANCE.md | docs/ACCEPTANCE.md does not exist |
| docs/internal/updates/UPDATE_10.md:88 | backtick | docs/updates/UPDATE_06.md | docs/updates/UPDATE_06.md does not exist |
| docs/internal/updates/UPDATE_11.md:5 | backtick | docs/updates/UPDATE_11.md | docs/updates/UPDATE_11.md does not exist |
| docs/internal/updates/UPDATE_11.md:51 | backtick | docs/recruiting_messages.md | docs/recruiting_messages.md does not exist |
| docs/internal/updates/UPDATE_14.md:13 | backtick | docs/updates/UPDATE_14.md | docs/updates/UPDATE_14.md does not exist |
| docs/internal/updates/UPDATE_14.md:62 | backtick | docs/JUDGE_SCORECARD.md | docs/JUDGE_SCORECARD.md does not exist |
| docs/internal/updates/UPDATE_14.md:62 | backtick | docs/ACCEPTANCE.md | docs/ACCEPTANCE.md does not exist |
| docs/internal/updates/UPDATE_14.md:75 | backtick | docs/internal/reviews/DESIGN_REVIEW_02.md | docs/internal/reviews/DESIGN_REVIEW_02.md does not exist |
| docs/internal/updates/UPDATE_14.md:87 | backtick | docs/video/SHOTLIST.md | docs/video/SHOTLIST.md does not exist |
| docs/internal/updates/UPDATE_14.md:88 | backtick | docs/video/clips/ | docs/video/clips does not exist |
| docs/internal/updates/UPDATE_14.md:89 | backtick | docs/video/rough_cut.mp4 | docs/video/rough_cut.mp4 does not exist |
| docs/internal/updates/UPDATE_14.md:90 | backtick | docs/video/RECORD_AT_THE_CREEK.md | docs/video/RECORD_AT_THE_CREEK.md does not exist |
| docs/internal/updates/UPDATE_14.md:97 | backtick | docs/ALEX_TODO.md | docs/ALEX_TODO.md does not exist |
| docs/internal/updates/UPDATE_16A.md:7 | backtick | docs/internal/reviews/patches/ | docs/internal/reviews/patches exists here but is not tracked |
| docs/internal/updates/UPDATE_16A.md:15 | backtick | docs/internal/reviews/REVIEW_02.md | docs/internal/reviews/REVIEW_02.md does not exist |
| docs/internal/updates/UPDATE_16A.md:31 | backtick | docs/MASTER_BRIEF.md | docs/MASTER_BRIEF.md does not exist |
| docs/internal/updates/UPDATE_16A.md:35 | backtick | results/harden/flaky.md | results/harden/flaky.md exists here but is not tracked |
| docs/internal/updates/UPDATE_16A.md:39 | backtick | results/harden/lighthouse.md | results/harden/lighthouse.md exists here but is not tracked |
| docs/internal/updates/UPDATE_16A.md:40 | backtick | results/harden/load.md | results/harden/load.md exists here but is not tracked |
| docs/internal/updates/UPDATE_16A.md:41 | backtick | docs/internal/reviews/A11Y_00.md | docs/internal/reviews/A11Y_00.md exists here but is not tracked |
| docs/internal/updates/UPDATE_16A.md:42 | backtick | docs/internal/reviews/LINKS_00.md | docs/internal/reviews/LINKS_00.md exists here but is not tracked |
| docs/internal/updates/UPDATE_16A.md:43 | backtick | docs/ACCEPTANCE.md | docs/ACCEPTANCE.md does not exist |
| docs/internal/updates/UPDATE_16A.md:44 | backtick | results/harden/costs.md | results/harden/costs.md exists here but is not tracked |

## Blocked, check by hand

| File and line | Kind | Link | What happened |
|---|---|---|---|
| docs/internal/reports/20260921T053423Z.md:118 | url | https://dash.cloudflare.com/profile/api-tokens | 403, the site refuses scripts |

## Skipped on purpose

| File and line | Kind | Link | What happened |
|---|---|---|---|
| README.md:55 | url | http://localhost:3100 | local or example address |
| docs/ig_proposal.md:89 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/internal/CONTEXT_LEDGER.md:24 | url | http://127.0.0.1:8100 | local or example address |
| docs/internal/recruiting_messages.md:8 | url | https://SITE_URL/?src=chat | template, not a real address |
| docs/internal/recruiting_messages.md:13 | url | https://SITE_URL/?src=friends | template, not a real address |
| docs/internal/recruiting_messages.md:18 | url | https://SITE_URL/?src=chat | template, not a real address |
| docs/internal/recruiting_messages.md:30 | url | https://SITE_URL/?src=creek_group | template, not a real address |
| docs/internal/recruiting_messages.md:45 | url (in code) | https://SITE_URL/?src=poster | template, not a real address |
| docs/internal/reviews/REVIEW_01.md:170 | url (in code) | http://localhost:8000/api/check/draft | local or example address |
| docs/internal/reviews/REVIEW_01.md:171 | url (in code) | http://localhost:8000/api/spot/spot-723166bb5214 | local or example address |
| docs/internal/reviews/REVIEW_01.md:203 | url (in code) | http://localhost:8000/api/test/export | local or example address |
| docs/internal/reviews/REVIEW_01.md:234 | url (in code) | http://localhost:3000/ | local or example address |
| docs/internal/reviews/REVIEW_01.md:238 | url (in code) | http://localhost:8000 | local or example address |
| docs/internal/reviews/REVIEW_01.md:276 | url (in code) | http://localhost:3000/_next/static/chunks/0fhk4zxv1y9up.js | local or example address |
| docs/notes/p2_validator_run.md:45 | url (in code) | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:46 | url (in code) | http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:100 | url | http://hl7.org/fhir/StructureDefinition/DomainResource | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:104 | url | http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType%7C3.0.0 | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:104 | url | http://snomed.info/sct#420531007 | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:160 | url (in code) | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:178 | url | http://hl7.eu/fhir/ig/oah/ValueSet/oah-indicators-no-health-oah-vs | FHIR canonical or namespace, a name |
| docs/notes/p2_validator_run.md:178 | url | https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look#artificial-bank | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:22 | url (in code) | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-oah | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:33 | url (in code) | http://www.w3.org/1999/xhtml\ | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:37 | url (in code) | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-size | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:44 | url (in code) | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-numberOfRecords | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:48 | url (in code) | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:51 | url (in code) | https://github.com/alejandro-publius/second-look/fhir/library-id | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:62 | url (in code) | http://terminology.hl7.org/CodeSystem/library-type | FHIR canonical or namespace, a name |
| docs/notes/sandbox_library.md:107 | url (in code) | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:109 | url (in code) | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:110 | url (in code) | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
