# Link check 00

Checked 2026-09-24T07:51:04Z at commit 2992321 by `uv run python scripts/harden_links.py`, over README.md and every tracked Markdown file under docs/ (106 files). Nothing was fixed. Raw rows: `results/harden/links.json`.

Relative links are resolved from the file that holds them and their #anchors are checked against the target's headings the way GitHub makes them. Paths in backticks are resolved from the repo root. Each web address got one GET with redirects followed. A site that answers 401, 403, 405, 429 or 999 to a script is listed as blocked, not dead: open it by hand. A path that git ignores (build output, local data) is listed as ignored, not dead. api.enora-oah.eu and the Resilience Map API were never called (hard rule 9); the HL7 sandbox got at most one GET a second and 50 in all (hard rule 10).

## Counts

| Kind | ok | dead | blocked | private | ignored | skipped |
|---|---|---|---|---|---|---|
| relative | 19 | 0 | 0 | 0 | 0 | 0 |
| backtick | 1365 | 81 | 0 | 0 | 33 | 0 |
| url | 266 | 116 | 22 | 7 | 0 | 125 |

## Dead, in the README and product docs

None.

## Dead, in docs/internal (working notes)

| File and line | Kind | Link | What happened |
|---|---|---|---|
| docs/internal/DONE.md:154 | backtick | docs/MODEL_CARD.md | docs/MODEL_CARD.md does not exist |
| docs/internal/DONE.md:155 | backtick | docs/THREAT_MODEL.md | docs/THREAT_MODEL.md does not exist |
| docs/internal/DONE.md:156 | backtick | docs/REPORT.pdf | docs/REPORT.pdf does not exist |
| docs/internal/DONE.md:157 | backtick | docs/DATA_CARD.md | docs/DATA_CARD.md does not exist |
| docs/internal/KILL_TESTS.md:14 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/KILL_TESTS.md:16 | backtick | photos/probe/ | photos/probe does not exist |
| docs/internal/MASTER_BRIEF.md:7 | backtick | docs/MASTER_BRIEF.md | docs/MASTER_BRIEF.md does not exist |
| docs/internal/MASTER_BRIEF.md:7 | backtick | fhir/citizen_followercity_spike.fsh | fhir/citizen_followercity_spike.fsh does not exist |
| docs/internal/MASTER_BRIEF.md:133 | backtick | results/key_agreement.json | results/key_agreement.json does not exist |
| docs/internal/MASTER_BRIEF.md:233 | backtick | docs/notes/their_image_model.md | docs/notes/their_image_model.md does not exist |
| docs/internal/alex_today.md:32 | backtick | docs/KILL_TESTS.md | docs/KILL_TESTS.md does not exist |
| docs/internal/alex_today.md:51 | backtick | docs/notes/devpost_fields.md | docs/notes/devpost_fields.md does not exist |
| docs/internal/alex_today.md:52 | backtick | docs/notes/slack.md | docs/notes/slack.md does not exist |
| docs/internal/alex_today.md:53 | backtick | docs/notes/their_image_model.md | docs/notes/their_image_model.md does not exist |
| docs/internal/alex_today.md:58 | backtick | docs/recruiting_messages.md | docs/recruiting_messages.md does not exist |
| docs/internal/reports/20260921T043754Z.md:9 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reports/20260921T061626Z.md:47 | backtick | docs/DEPTH_MAP.md | docs/DEPTH_MAP.md does not exist |
| docs/internal/reviews/A11Y_00.md:9 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/DESIGN_REVIEW_01.md:6 | backtick | docs/updates/UPDATE_06.md | docs/updates/UPDATE_06.md does not exist |
| docs/internal/reviews/JUDGE_SIM_00_before.md:58 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:58 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:80 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-79t.pages.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:124 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:124 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-79t.pages.dev/_next/static/chunks/*.js | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/health | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:146 | url | https://second-look-api.thealexschroeder.workers.dev/ | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/city/strawberry-creek | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/api/health | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-79t.pages.dev/nonexistent-page-xyz | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/JUDGE_SIM_00_before.md:168 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:21 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:25 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:32 | url | https://www.cal-ipc.org/plants/profile/tradescantia-fluminensis-profile/ | 404 |
| docs/internal/reviews/LINKS_00.md:33 | url | https://commons.wikimedia.org/wiki/File:North_Creek | 404 |
| docs/internal/reviews/LINKS_00.md:34 | url | https://commons.wikimedia.org/wiki/File:Vincent_Creek | 404 |
| docs/internal/reviews/LINKS_00.md:44 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:56 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:58 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:60 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:61 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:62 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:64 | url | https://second-look-79t.pages.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/LINKS_00.md:68 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:69 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:70 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:71 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:72 | url | https://second-look-79t.pages.dev/_next/static/chunks/*.js | 404 |
| docs/internal/reviews/LINKS_00.md:73 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:74 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:75 | url | https://second-look-api.thealexschroeder.workers.dev/api/health | 404 |
| docs/internal/reviews/LINKS_00.md:76 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/LINKS_00.md:77 | url | https://second-look-api.thealexschroeder.workers.dev/ | 404 |
| docs/internal/reviews/LINKS_00.md:78 | url | https://second-look-79t.pages.dev/city/strawberry-creek | 404 |
| docs/internal/reviews/LINKS_00.md:79 | url | https://second-look-79t.pages.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/LINKS_00.md:80 | url | https://second-look-79t.pages.dev/api/health | 404 |
| docs/internal/reviews/LINKS_00.md:81 | url | https://second-look-79t.pages.dev/nonexistent-page-xyz | 404 |
| docs/internal/reviews/LINKS_00.md:82 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:83 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:84 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:85 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:87 | url | https://www.cal-ipc.org/plants/profile/tradescantia-fluminensis-profile/ | 404 |
| docs/internal/reviews/LINKS_00.md:88 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:89 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:90 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:91 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:92 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:94 | url | https://second-look-79t.pages.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/LINKS_00.md:96 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:97 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:98 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:99 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:100 | url | https://second-look-79t.pages.dev/_next/static/chunks/*.js | 404 |
| docs/internal/reviews/LINKS_00.md:101 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:103 | url | https://second-look-api.thealexschroeder.workers.dev/api/health | 404 |
| docs/internal/reviews/LINKS_00.md:104 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/LINKS_00.md:105 | url | https://second-look-api.thealexschroeder.workers.dev/ | 404 |
| docs/internal/reviews/LINKS_00.md:106 | url | https://second-look-79t.pages.dev/city/strawberry-creek | 404 |
| docs/internal/reviews/LINKS_00.md:107 | url | https://second-look-79t.pages.dev/api/fhir/Bundle/example | 404 |
| docs/internal/reviews/LINKS_00.md:108 | url | https://second-look-79t.pages.dev/api/health | 404 |
| docs/internal/reviews/LINKS_00.md:109 | url | https://second-look-79t.pages.dev/nonexistent-page-xyz | 404 |
| docs/internal/reviews/LINKS_00.md:110 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example | 404 |
| docs/internal/reviews/LINKS_00.md:111 | url | https://second-look-api.thealexschroeder.workers.dev/api/spot/example/fhir | 404 |
| docs/internal/reviews/LINKS_00.md:114 | url | https://second-look-api.thealexschroeder.workers.dev/api/test/export | 404 |
| docs/internal/reviews/LINKS_00.md:115 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:119 | url | https://commons.wikimedia.org/wiki/File:Stormwater_outfall_-_geograph | 404 |
| docs/internal/reviews/LINKS_00.md:120 | url | https://a.nel.cloudflare.com | 404 |
| docs/internal/reviews/LINKS_00.md:121 | url | https://evil.example | ConnectError |
| docs/internal/reviews/LINKS_00.md:124 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:126 | url | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/LINKS_00.md:180 | url | https://commons.wikimedia.org/wiki/File:FlorhamParkSewerageUtilityOutfall.webm,https://upload.wikimedia.org/wikipedia/commons/c/c9/FlorhamParkSewerageUtilityOutfall.webm?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Z22,CC | 404 |
| docs/internal/reviews/LINKS_00.md:181 | url | https://commons.wikimedia.org/wiki/File:Crows_and_Bagmati_River.webm,https://upload.wikimedia.org/wikipedia/commons/7/7f/Crows_and_Bagmati_River.webm?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Ashma | 404 |
| docs/internal/reviews/LINKS_00.md:182 | url | https://commons.wikimedia.org/wiki/File:North_Creek | 404 |
| docs/internal/reviews/LINKS_00.md:183 | url | https://commons.wikimedia.org/wiki/File:Salmon_River_wood_jam_%26_side_channel_restoration_project_at_Wildwood.webm,https://upload.wikimedia.org/wikipedia/commons/d/d7/Salmon_River_wood_jam_%26_side_channel_restoration_project_at_Wildwood.webm?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Bureau | 404 |
| docs/internal/reviews/LINKS_00.md:184 | url | https://commons.wikimedia.org/wiki/File:Vincent_Creek | 404 |
| docs/internal/reviews/LINKS_00.md:185 | url | https://commons.wikimedia.org/wiki/File:Sonoma_Creek_-_January_5_2023_-_Sarah_Stierch.webm,https://upload.wikimedia.org/wikipedia/commons/3/3e/Sonoma_Creek_-_January_5_2023_-_Sarah_Stierch.webm?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Missvain,CC | 404 |
| docs/internal/reviews/LINKS_00.md:186 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek10.JPG,https://upload.wikimedia.org/wikipedia/commons/8/8e/StrawberryCreek10.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/reviews/LINKS_00.md:187 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek12.JPG,https://upload.wikimedia.org/wikipedia/commons/7/7b/StrawberryCreek12.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/reviews/LINKS_00.md:188 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek3.JPG,https://upload.wikimedia.org/wikipedia/commons/2/2a/StrawberryCreek3.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/reviews/LINKS_00.md:189 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek6.JPG,https://upload.wikimedia.org/wikipedia/commons/a/af/StrawberryCreek6.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/reviews/LINKS_00.md:190 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek8.JPG,https://upload.wikimedia.org/wikipedia/commons/b/b5/StrawberryCreek8.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/reviews/LINKS_00.md:191 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek9.JPG,https://upload.wikimedia.org/wikipedia/commons/a/a4/StrawberryCreek9.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/reviews/LINKS_00.md:192 | url | https://commons.wikimedia.org/wiki/File:Strawberry_Creek_Estuary_Berkeley.jpg,https://upload.wikimedia.org/wikipedia/commons/d/d6/Strawberry_Creek_Estuary_Berkeley.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Awinch1001,CC0,,The | 404 |
| docs/internal/reviews/REVIEW_01.md:7 | backtick | docs/BUILD_LOG.md | docs/BUILD_LOG.md does not exist |
| docs/internal/reviews/REVIEW_01.md:684 | backtick | results/placeholder_hashes.json | results/placeholder_hashes.json does not exist |
| docs/internal/reviews/REVIEW_02.md:17 | url (in code) | https://second-look-api.thealexschroeder.workers.dev/api/test/export | 404 |
| docs/internal/reviews/REVIEW_02.md:200 | url (in code) | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/REVIEW_02.md:330 | backtick | results/usability_20261001.json | results/usability_20261001.json does not exist |
| docs/internal/reviews/REVIEW_02.md:341 | backtick | results/consensus_20261001.json | results/consensus_20261001.json does not exist |
| docs/internal/reviews/REVIEW_02.md:604 | url (in code) | https://commons.wikimedia.org/wiki/File:Stormwater_outfall_-_geograph | 404 |
| docs/internal/reviews/REVIEW_02.md:702 | url (in code) | https://a.nel.cloudflare.com | 404 |
| docs/internal/reviews/REVIEW_02.md:879 | url (in code) | https://evil.example | ConnectError |
| docs/internal/reviews/REVIEW_02.md:956 | backtick | core/rainfall | core/rainfall does not exist |
| docs/internal/reviews/REVIEW_02.md:1112 | backtick | scripts/check_words.py | scripts/check_words.py does not exist |
| docs/internal/reviews/REVIEW_02.md:1144 | url (in code) | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/REVIEW_02.md:1165 | backtick | results/key_agreement.json | results/key_agreement.json does not exist |
| docs/internal/reviews/REVIEW_02.md:1252 | url (in code) | https://second-look-api.thealexschroeder.workers.dev | 404 |
| docs/internal/reviews/REVIEW_02.md:1455 | backtick | docs/internal/reviews/patches/NN-name.patch | docs/internal/reviews/patches/NN-name.patch does not exist |
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
| docs/internal/updates/UPDATE_10.md:88 | backtick | docs/updates/UPDATE_06.md | docs/updates/UPDATE_06.md does not exist |
| docs/internal/updates/UPDATE_11.md:5 | backtick | docs/updates/UPDATE_11.md | docs/updates/UPDATE_11.md does not exist |
| docs/internal/updates/UPDATE_11.md:51 | backtick | docs/recruiting_messages.md | docs/recruiting_messages.md does not exist |
| docs/internal/updates/UPDATE_14.md:13 | backtick | docs/updates/UPDATE_14.md | docs/updates/UPDATE_14.md does not exist |
| docs/internal/updates/UPDATE_15.md:7 | backtick | docs/updates/ | docs/updates does not exist |
| docs/internal/updates/UPDATE_16A.md:31 | backtick | docs/MASTER_BRIEF.md | docs/MASTER_BRIEF.md does not exist |
| docs/internal/updates/UPDATE_18.md:27 | backtick | docs/reports/ | docs/reports does not exist |
| docs/internal/updates/UPDATE_18.md:32 | backtick | docs/internal/STATUS.md | docs/internal/STATUS.md does not exist |
| docs/internal/updates/UPDATE_18.md:46 | backtick | docs/video/CREEK_30_MIN.md | docs/video/CREEK_30_MIN.md does not exist |
| docs/internal/updates/UPDATE_18.md:47 | backtick | docs/submission/DEVPOST_PASTE.md | docs/submission/DEVPOST_PASTE.md does not exist |
| docs/internal/updates/UPDATE_18.md:57 | backtick | docs/updates/ | docs/updates does not exist |
| docs/internal/updates/UPDATE_18.md:71 | backtick | docs/internal/reviews/JUDGE_SIM_01_after.md | docs/internal/reviews/JUDGE_SIM_01_after.md does not exist |
| docs/internal/updates/UPDATE_18.md:77 | backtick | docs/internal/WHEN_ALEX_IS_BACK.md | docs/internal/WHEN_ALEX_IS_BACK.md does not exist |
| docs/internal/updates/UPDATE_22.md:40 | backtick | docs/video/CREEK_30_MIN.md | docs/video/CREEK_30_MIN.md does not exist |
| docs/internal/updates/UPDATE_22.md:40 | backtick | docs/internal/WHEN_ALEX_IS_BACK.md | docs/internal/WHEN_ALEX_IS_BACK.md does not exist |
| docs/internal/updates/UPDATE_22.md:50 | url | https://commons.wikimedia.org/wiki/File:FlorhamParkSewerageUtilityOutfall.webm,https://upload.wikimedia.org/wikipedia/commons/c/c9/FlorhamParkSewerageUtilityOutfall.webm?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Z22,CC | 404 |
| docs/internal/updates/UPDATE_22.md:51 | url | https://commons.wikimedia.org/wiki/File:Crows_and_Bagmati_River.webm,https://upload.wikimedia.org/wikipedia/commons/7/7f/Crows_and_Bagmati_River.webm?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Ashma | 404 |
| docs/internal/updates/UPDATE_22.md:52 | url | https://commons.wikimedia.org/wiki/File:North_Creek | 404 |
| docs/internal/updates/UPDATE_22.md:53 | url | https://commons.wikimedia.org/wiki/File:Salmon_River_wood_jam_%26_side_channel_restoration_project_at_Wildwood.webm,https://upload.wikimedia.org/wikipedia/commons/d/d7/Salmon_River_wood_jam_%26_side_channel_restoration_project_at_Wildwood.webm?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Bureau | 404 |
| docs/internal/updates/UPDATE_22.md:54 | url | https://commons.wikimedia.org/wiki/File:Vincent_Creek | 404 |
| docs/internal/updates/UPDATE_22.md:55 | url | https://commons.wikimedia.org/wiki/File:Sonoma_Creek_-_January_5_2023_-_Sarah_Stierch.webm,https://upload.wikimedia.org/wikipedia/commons/3/3e/Sonoma_Creek_-_January_5_2023_-_Sarah_Stierch.webm?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Missvain,CC | 404 |
| docs/internal/updates/UPDATE_22.md:56 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek10.JPG,https://upload.wikimedia.org/wikipedia/commons/8/8e/StrawberryCreek10.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/updates/UPDATE_22.md:57 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek12.JPG,https://upload.wikimedia.org/wikipedia/commons/7/7b/StrawberryCreek12.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/updates/UPDATE_22.md:58 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek3.JPG,https://upload.wikimedia.org/wikipedia/commons/2/2a/StrawberryCreek3.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/updates/UPDATE_22.md:59 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek6.JPG,https://upload.wikimedia.org/wikipedia/commons/a/af/StrawberryCreek6.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/updates/UPDATE_22.md:60 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek8.JPG,https://upload.wikimedia.org/wikipedia/commons/b/b5/StrawberryCreek8.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/updates/UPDATE_22.md:61 | url | https://commons.wikimedia.org/wiki/File:StrawberryCreek9.JPG,https://upload.wikimedia.org/wikipedia/commons/a/a4/StrawberryCreek9.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Coro,CC | 404 |
| docs/internal/updates/UPDATE_22.md:62 | url | https://commons.wikimedia.org/wiki/File:Strawberry_Creek_Estuary_Berkeley.jpg,https://upload.wikimedia.org/wikipedia/commons/d/d6/Strawberry_Creek_Estuary_Berkeley.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original,Awinch1001,CC0,,The | 404 |
| docs/internal/updates/UPDATE_27.md:23 | backtick | docs/internal/updates/UPDATE_23.md | docs/internal/updates/UPDATE_23.md does not exist |
| docs/internal/updates/UPDATE_29.md:50 | backtick | docs/MODEL_CARD.md | docs/MODEL_CARD.md does not exist |
| docs/internal/updates/UPDATE_29.md:51 | backtick | docs/THREAT_MODEL.md | docs/THREAT_MODEL.md does not exist |
| docs/internal/updates/UPDATE_29.md:52 | backtick | docs/REPORT.pdf | docs/REPORT.pdf does not exist |
| docs/internal/updates/UPDATE_29.md:53 | backtick | docs/DATA_CARD.md | docs/DATA_CARD.md does not exist |

## Blocked, check by hand

| File and line | Kind | Link | What happened |
|---|---|---|---|
| README.md:554 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/THIRD_PARTY.md:11 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/MASTER_BRIEF.md:66 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Provenance/465 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:19 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:22 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:27 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:28 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:30 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:31 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:48 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:65 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:66 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Provenance/465 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:118 | url | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Observation/12 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/LINKS_00.md:205 | url | https://a.nel.cloudflare.com/report/v4?s=ZuHl | 405, the site refuses scripts |
| docs/internal/reviews/REVIEW_02.md:549 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Observation/12 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/internal/reviews/REVIEW_02.md:703 | url (in code) | https://a.nel.cloudflare.com/report/v4?s=ZuHl | 405, the site refuses scripts |
| docs/notes/sandbox_library.md:6 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/notes/sandbox_library.md:10 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466 | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/notes/sandbox_library.md:126 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |
| docs/notes/sandbox_library.md:127 | url (in code) | https://sandbox.hl7europe.eu/oneaquahealth/fhir | the name does not resolve (NXDOMAIN at their own nameserver since 2026-09-23; hl7-eu/oah issue 8) |

## Skipped on purpose

| File and line | Kind | Link | What happened |
|---|---|---|---|
| README.md:13 | url | https://github.com/alejandro-publius/second-look/actions/workflows/check.yml/badge.svg | a name under our repo address, not a page |
| README.md:13 | url | https://github.com/alejandro-publius/second-look/actions/workflows/check.yml | a name under our repo address, not a page |
| README.md:514 | url | http://localhost:3100 | local or example address |
| README.md:514 | url | http://localhost:3100/city?creek=strawberry-creek | local or example address |
| docs/ig_proposal.md:89 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/internal/CONTEXT_LEDGER.md:24 | url | http://127.0.0.1:8100 | local or example address |
| docs/internal/recruiting_messages.md:8 | url | https://SITE_URL/?src=chat | template, not a real address |
| docs/internal/recruiting_messages.md:13 | url | https://SITE_URL/?src=friends | template, not a real address |
| docs/internal/recruiting_messages.md:18 | url | https://SITE_URL/?src=chat | template, not a real address |
| docs/internal/recruiting_messages.md:30 | url | https://SITE_URL/?src=creek_group | template, not a real address |
| docs/internal/recruiting_messages.md:45 | url (in code) | https://SITE_URL/?src=poster | template, not a real address |
| docs/internal/reviews/JUDGE_SIM_00_before.md:93 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/internal/reviews/JUDGE_SIM_00_before.md:102 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/internal/reviews/LINKS_00.md:29 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/internal/reviews/LINKS_00.md:63 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/internal/reviews/LINKS_00.md:67 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/internal/reviews/LINKS_00.md:86 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/internal/reviews/LINKS_00.md:93 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/internal/reviews/LINKS_00.md:95 | url | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/internal/reviews/LINKS_00.md:211 | url | https://github.com/alejandro-publius/second-look/actions/workflows/check.yml/badge.svg | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:212 | url | https://github.com/alejandro-publius/second-look/actions/workflows/check.yml | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:213 | url | http://localhost:3100 | local or example address |
| docs/internal/reviews/LINKS_00.md:214 | url | http://localhost:3100/city?creek=strawberry-creek | local or example address |
| docs/internal/reviews/LINKS_00.md:215 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:216 | url | http://127.0.0.1:8100 | local or example address |
| docs/internal/reviews/LINKS_00.md:217 | url | https://SITE_URL/?src=chat | template, not a real address |
| docs/internal/reviews/LINKS_00.md:218 | url | https://SITE_URL/?src=friends | template, not a real address |
| docs/internal/reviews/LINKS_00.md:219 | url | https://SITE_URL/?src=chat | template, not a real address |
| docs/internal/reviews/LINKS_00.md:220 | url | https://SITE_URL/?src=creek_group | template, not a real address |
| docs/internal/reviews/LINKS_00.md:221 | url | https://SITE_URL/?src=poster | template, not a real address |
| docs/internal/reviews/LINKS_00.md:222 | url | http://localhost:3100 | local or example address |
| docs/internal/reviews/LINKS_00.md:223 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:224 | url | http://127.0.0.1:8100 | local or example address |
| docs/internal/reviews/LINKS_00.md:225 | url | https://SITE_URL/?src=chat | template, not a real address |
| docs/internal/reviews/LINKS_00.md:226 | url | https://SITE_URL/?src=friends | template, not a real address |
| docs/internal/reviews/LINKS_00.md:227 | url | https://SITE_URL/?src=chat | template, not a real address |
| docs/internal/reviews/LINKS_00.md:228 | url | https://SITE_URL/?src=creek_group | template, not a real address |
| docs/internal/reviews/LINKS_00.md:229 | url | https://SITE_URL/?src=poster | template, not a real address |
| docs/internal/reviews/LINKS_00.md:230 | url | http://localhost:8000/api/check/draft | local or example address |
| docs/internal/reviews/LINKS_00.md:231 | url | http://localhost:8000/api/spot/spot-723166bb5214 | local or example address |
| docs/internal/reviews/LINKS_00.md:232 | url | http://localhost:8000/api/test/export | local or example address |
| docs/internal/reviews/LINKS_00.md:233 | url | http://localhost:3000/ | local or example address |
| docs/internal/reviews/LINKS_00.md:234 | url | http://localhost:8000 | local or example address |
| docs/internal/reviews/LINKS_00.md:235 | url | http://localhost:3000/_next/static/chunks/0fhk4zxv1y9up.js | local or example address |
| docs/internal/reviews/LINKS_00.md:236 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:237 | url | http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:238 | url | http://hl7.org/fhir/StructureDefinition/DomainResource | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:239 | url | http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType%7C3.0.0 | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:240 | url | http://snomed.info/sct#420531007 | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:241 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:242 | url | http://hl7.eu/fhir/ig/oah/ValueSet/oah-indicators-no-health-oah-vs | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:243 | url | https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look#artificial-bank | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:244 | url | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-oah | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:245 | url | http://www.w3.org/1999/xhtml\ | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:246 | url | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-size | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:247 | url | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-numberOfRecords | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:248 | url | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:249 | url | https://github.com/alejandro-publius/second-look/fhir/library-id | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:250 | url | http://terminology.hl7.org/CodeSystem/library-type | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:251 | url | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:252 | url | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:253 | url | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:254 | url | http://localhost:8000/api/check/draft | local or example address |
| docs/internal/reviews/LINKS_00.md:255 | url | http://localhost:8000/api/spot/spot-723166bb5214 | local or example address |
| docs/internal/reviews/LINKS_00.md:256 | url | http://localhost:8000/api/test/export | local or example address |
| docs/internal/reviews/LINKS_00.md:257 | url | http://localhost:3000/ | local or example address |
| docs/internal/reviews/LINKS_00.md:258 | url | http://localhost:8000 | local or example address |
| docs/internal/reviews/LINKS_00.md:259 | url | http://localhost:3000/_next/static/chunks/0fhk4zxv1y9up.js | local or example address |
| docs/internal/reviews/LINKS_00.md:260 | url | http://127.0.0.1:8977/api/photo/up-5f0f1777f2bd55a0?t=A_HT | local or example address |
| docs/internal/reviews/LINKS_00.md:261 | url | http://localhost:8085/fhir} | local or example address |
| docs/internal/reviews/LINKS_00.md:262 | url | http://127.0.0.1:8911/api/test/export?token=change-me-long-random | local or example address |
| docs/internal/reviews/LINKS_00.md:263 | url | http://127.0.0.1:8931/api/photo/%E0%A4?t=x | local or example address |
| docs/internal/reviews/LINKS_00.md:264 | url | http://127.0.0.1:8947/api/skeleton/ping | local or example address |
| docs/internal/reviews/LINKS_00.md:265 | url | http://localhost:8000 | local or example address |
| docs/internal/reviews/LINKS_00.md:266 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:267 | url | http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:268 | url | http://hl7.org/fhir/StructureDefinition/DomainResource | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:269 | url | http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType%7C3.0.0 | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:270 | url | http://snomed.info/sct#420531007 | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:271 | url | http://unitsofmeasure.org | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:272 | url | http://hl7.eu/fhir/ig/oah/ValueSet/oah-indicators-no-health-oah-vs | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:273 | url | https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look#artificial-bank | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:274 | url | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-oah | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:275 | url | http://www.w3.org/1999/xhtml\ | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:276 | url | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-size | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:277 | url | http://hl7.eu/fhir/ig/oah/StructureDefinition/library-numberOfRecords | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:278 | url | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:279 | url | https://github.com/alejandro-publius/second-look/fhir/library-id | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:280 | url | http://terminology.hl7.org/CodeSystem/library-type | FHIR canonical or namespace, a name |
| docs/internal/reviews/LINKS_00.md:281 | url | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:282 | url | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:283 | url | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
| docs/internal/reviews/LINKS_00.md:284 | url | https://github.com/alejandro-publius/second-look/actions | a name under our repo address, not a page |
| docs/internal/reviews/REVIEW_01.md:170 | url (in code) | http://localhost:8000/api/check/draft | local or example address |
| docs/internal/reviews/REVIEW_01.md:171 | url (in code) | http://localhost:8000/api/spot/spot-723166bb5214 | local or example address |
| docs/internal/reviews/REVIEW_01.md:203 | url (in code) | http://localhost:8000/api/test/export | local or example address |
| docs/internal/reviews/REVIEW_01.md:234 | url (in code) | http://localhost:3000/ | local or example address |
| docs/internal/reviews/REVIEW_01.md:238 | url (in code) | http://localhost:8000 | local or example address |
| docs/internal/reviews/REVIEW_01.md:276 | url (in code) | http://localhost:3000/_next/static/chunks/0fhk4zxv1y9up.js | local or example address |
| docs/internal/reviews/REVIEW_02.md:362 | url (in code) | http://127.0.0.1:8977/api/photo/up-5f0f1777f2bd55a0?t=A_HT | local or example address |
| docs/internal/reviews/REVIEW_02.md:549 | url (in code) | http://localhost:8085/fhir} | local or example address |
| docs/internal/reviews/REVIEW_02.md:846 | url (in code) | http://127.0.0.1:8911/api/test/export?token=change-me-long-random | local or example address |
| docs/internal/reviews/REVIEW_02.md:945 | url (in code) | http://127.0.0.1:8931/api/photo/%E0%A4?t=x | local or example address |
| docs/internal/reviews/REVIEW_02.md:1143 | url (in code) | http://127.0.0.1:8947/api/skeleton/ping | local or example address |
| docs/internal/reviews/REVIEW_02.md:1252 | url (in code) | http://localhost:8000 | local or example address |
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
| docs/notes/sandbox_library.md:90 | url (in code) | https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle | a base inside the copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> (worker/src/index.ts) |
| docs/notes/sandbox_library.md:107 | url (in code) | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:109 | url (in code) | https://github.com/alejandro-publius/second-look%7Csecond-look | a name under our repo address, not a page |
| docs/notes/sandbox_library.md:110 | url (in code) | https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks | a name under our repo address, not a page |
| docs/submission/JUDGE_QA.md:92 | url | https://github.com/alejandro-publius/second-look/actions | a name under our repo address, not a page |
