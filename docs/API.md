# HTTP API

Two servers answer the same questions. The **Worker** (`worker/src/index.ts`, TypeScript on
Cloudflare Workers with D1 and KV) is what the live site uses, under `/api` on the site's own
origin. The **Python API** (`apps/api/`, FastAPI) is the reference: the tests, the evals and
`make dev` run it, and the Worker's pure parts are ports of it, proved equal by golden vectors
(`worker/golden/`, `make worker-check`).

`scripts/api_inventory.py` reads both route lists out of the code, and
`scripts/tests/test_api_docs.py` fails when a route has no row below, or a row has no route.
The counts: the Worker answers <!--v:results/api_inventory.json#/worker/count-->28<!--/v--> routes
and the Python API <!--v:results/api_inventory.json#/python/count-->29<!--/v-->
(`results/api_inventory.json`).

Every answer is JSON unless the row says otherwise. An error is `{"detail": "..."}` in plain
words. Nothing here takes a name, an email, an address or free text; see `docs/DATA_HANDLING.md`
for what each table holds and `SECURITY.md` for the secrets and the lock.

## The Worker (production)

"any" means the Worker does not check the method; the web app sends GET. The Worker has no rate
limit, on purpose: counting per visitor would mean holding something that identifies them
(`docs/DATA_HANDLING.md`, "The rate limit"). Cloudflare's own edge protection sits in front.

| Method | Path | What it does | What it stores | Limit or lock |
|---|---|---|---|---|
| any | `/health` | Says the API is up. The landing page calls it to wake the Worker. | nothing | none |
| any | `/api/content/hash` | The hash of the test content the Worker serves. | nothing | none |
| POST | `/api/test/session` | Starts a two-minute test sitting: takes the next pre-registered arm and a shuffled item order. | a `session` row (arm, item order, consent version, hashes, coarse device class, source label, a hash of a random browser token) | the `x-qa-key` header, when it matches `QA_KEY`, marks the sitting as a test so it never counts |
| POST | `/api/test/response` | Stores one answer to one test photo. The first answer stays; a different second one gets 409. | a `response` row (item, yes, no or can't tell, timing, position) | none |
| POST | `/api/test/lesson-done` | Records the seconds spent on each lesson screen. | `session.lesson_seconds` | none |
| POST | `/api/test/complete` | Ends the sitting and returns the score per feature. With `keep_score`, hands back a new random contributor token. | `completed_at`, the optional prior experience answer; with `keep_score`, an `observer` row (token, four scores, date) not linked to the session | none |
| any | `/api/test/resume` | Where a reloaded sitting was. Read only: never makes a session or a token. | nothing | none |
| any | `/api/test/counts` | Sittings randomized and completed per arm and per source, tests left out. | nothing | none |
| any | `/api/test/export` | `sessions.csv` and `responses.csv` in one zip. | nothing | `?token=` must match `EXPORT_TOKEN`, or the answer is 404 |
| POST | `/api/demo/answer` | Judge mode: says only whether an answer was right, never the gold label. | nothing | the data lock: 403 before 2026-09-28T01:00:00Z |
| POST | `/api/t2/offer` | Part 2, the assisted second look: Start or No thanks after part 1's score. Start randomizes once per part 1 sitting from the pre-registered slots of that part 1 arm; a QA sitting may name its arm and takes no slot. | a `part2_session` row (part 1 arm, arm, item order, or the decline) | 409 until the part 1 sitting has reached its score screen |
| POST | `/api/t2/answer` | One first answer to one part 2 photo. Answers only whether the checker's question appears, never which way the checker leans. The first answer stays. | a `part2_response` row (first answer, whether the question was shown, timing, position) | none |
| POST | `/api/t2/choice` | Keep or Change after the question; the person's pick is stored. | the row's final answer, choice and time | 409 when no question was shown or a choice is already stored |
| POST | `/api/t2/complete` | Ends part 2 and returns the score out of 8, or the photos to send again. | `part2_session.completed_at` | none |
| any | `/api/t2/resume` | Where a reloaded part 2 was, with the photo whose question was showing. Read only. | nothing | none |
| any | `/api/t2/counts` | Part 2 started and finished per arm, and the declines, tests left out. | nothing | none |
| POST | `/api/t2/demo` | Part 2's judge mode: whether the question would appear, and whether an answer was right. | nothing | the data lock: 403 before 2026-09-28T01:00:00Z |
| POST | `/api/check/draft` | A creek check's answers: makes the spot if it is new, asks Open-Meteo about rain, and picks at most two follow-up questions by code. | a `spot` row if new (a coarse point unless the person placed the pin), a draft `visit` row (coded answers, first rating, the questions asked, the contributor token if given) | none |
| POST | `/api/check/finalize` | The answers to the follow-ups and the final rating; builds the FHIR Bundle. | `check_result` rows, the final rating, a `fhir_bundle` row | refuses an answer to a question it never asked |
| POST | `/api/quick/{spot_id}` | The three-question return check at a known spot: colour, smell, pipe running. | a `visit` row of kind quick | none |
| POST | `/api/upload` | A creek photo as the form field `file`. JPEG, PNG or WebP only. Camera metadata (EXIF, GPS, XMP, ICC, comments) is cut out. Returns the photo id and the one token that can read it. | the bytes in KV with a 30 day expiry; an `upload` row with a hash of the token | 8 MB at most |
| GET | `/api/photo/{photo_id}` | One uploaded photo, served private and uncached. | nothing | `?t=` must be that photo's token, or the answer is 404 |
| POST | `/api/walk` | A finished video walk, sent by the phone: `{walk_id, answers, answered_at, followup_answers, final_rating}`. Builds its demo record and returns its `record_id`. The store runs the creek check's follow-up rules on the answers itself (rain unknown, so the dry pipe question never; no score, no flag) and keeps the checks that ran with the phone's answers to them. A body with neither follow-up field keeps no checks. The same walk sent again returns the same id; other answers for the same walk and second get 409. Never counted and never mirrored to the sandbox. | a `walk_record` row (the walk id, the coded answers, the time, the demo Bundle) and a `walk_checks` row (the checks and the final rating), deleted together 30 days later | the body is 4096 bytes at most and holds nothing else; each answer must be a value from the form; a follow-up answer only for a question the rules asked, from the answers that question takes, and a final rating other than the first only with the rating check answered `change` (422 otherwise); the time at most 5 minutes ahead and 7 days old; 200 records a day on the whole server, then 429 |
| GET | `/api/walk/{record_id}` | One stored walk record: its answers, its demo Bundle, and `checks`, `first_rating` and `final_rating` as `/api/spot` gives them for a visit, until its delete date. | nothing | none |
| GET | `/api/walk/{record_id}/fhir` | The same stored walk record's demo Bundle alone, the FHIR its record's curl line fetches, until its delete date. It answers the rating question with the final rating, and names the first one in the response's text when the rating check changed it. | nothing | none |
| any | `/api/creeks` | Every creek with a record, with the visit ids behind each count. | nothing | none |
| any | `/api/city/{creek}` | The analyst's view of one creek: findings, what it needs in approved words, pipes worth testing, reaches, downstream notes. | nothing | none |
| GET | `/api/spot/{spot_id}` | One spot's record: each answer beside the observer's score, the health card, the place and the downstream notes. | nothing | none |
| any | `/api/spot/{spot_id}/fhir` | The latest visit at a spot as a FHIR Bundle. | nothing | none |
| any | `/api/fhir/Bundle/{visit_id}` | One visit as a FHIR Bundle. | nothing | none |
| any | `/api/fhir/validation` | The last HL7 validator run (`results/fhir_validation.json`). | nothing | none |
| any | `/api/fhir/referral/{spot_id}` | A ServiceRequest for a pipe on the worth testing list, made on request from stored visits. | nothing | none |
| any | `/api/fhir/referral/{spot_id}/example-result` | How a laboratory result would come back to that pipe. Tagged and labelled EXAMPLE. | nothing | none |
| any | `/api/two` | One of our Observations beside one laboratory Observation from their sandbox, read from the copy `scripts/cache_their_records.py` stored. Ours is from the latest stored visit; with none stored, it is the golden visit, made by hand, and `ours_example` is true so the page labels it an example. `ours_place` names the place. | nothing | none |
| GET | `/api/inaturalist/{creek}` | The iNaturalist context line for one creek: research-grade sightings of plants on the region's invasive list near its spots, read from the copy `scripts/cache_inaturalist.py` stored, with the fetch time. The sightings are withheld until the creek's record answers the invasive plant question. Context only: nothing counts it and nothing decides from it. | nothing | none |

## The Python API (reference)

Limits are per client address, over a sliding window, kept in process memory only and gone when
the process stops (`apps/api/security.py`). The address is hashed with a random salt and never
stored or logged.

| Limit | Requests | Window |
|---|---|---|
| study | <!--v:results/api_inventory.json#/rate_limits/study/limit-->60<!--/v--> | <!--v:results/api_inventory.json#/rate_limits/study/window_seconds-->10<!--/v--> seconds |
| read | <!--v:results/api_inventory.json#/rate_limits/read/limit-->60<!--/v--> | <!--v:results/api_inventory.json#/rate_limits/read/window_seconds-->10<!--/v--> seconds |
| demo | <!--v:results/api_inventory.json#/rate_limits/demo/limit-->30<!--/v--> | <!--v:results/api_inventory.json#/rate_limits/demo/window_seconds-->10<!--/v--> seconds |
| upload | <!--v:results/api_inventory.json#/rate_limits/upload/limit-->12<!--/v--> | <!--v:results/api_inventory.json#/rate_limits/upload/window_seconds-->60<!--/v--> seconds |

The routes do and store what the Worker's routes of the same path do, with the differences in
the table. The last column names the limit from the table above, then any lock.

| Method | Path | What it does | What it stores | Limit or lock |
|---|---|---|---|---|
| GET | `/health` | Says the API is up. | nothing | none |
| POST | `/api/skeleton/ping` | The walking skeleton on docker compose: one row written, the count read back. | one `skeleton_ping` row | none |
| GET | `/api/content/hash` | The content hash and the build hash. | nothing | read |
| POST | `/api/test/session` | Starts a sitting. The arm comes from `core/allocator.py` itself. | a `session` row | study; the `x-qa-key` header marks a test |
| POST | `/api/test/response` | One answer to one test photo. | a `response` row | study |
| POST | `/api/test/lesson-done` | Seconds per lesson screen. | `session.lesson_seconds` | study |
| POST | `/api/test/complete` | Ends the sitting, returns the score per feature, and with `keep_score` a contributor token. | `completed_at`; an `observer` row with `keep_score` | study |
| GET | `/api/test/resume` | Where a reloaded sitting was. Read only. | nothing | study |
| GET | `/api/test/counts` | Sittings per arm and per source. | nothing | read |
| GET | `/api/test/export` | The two CSV files in a zip. | nothing | read; `?token=` must match `EXPORT_TOKEN`, or 404 |
| POST | `/api/demo/answer` | Judge mode: right or not, never the label. Takes no database session. | nothing | demo; 403 before the data lock |
| POST | `/api/check/draft` | A creek check's answers and the follow-up questions. | `spot` if new, a draft `visit` | study |
| POST | `/api/check/finalize` | Follow-up answers and the final rating; writes the FHIR Bundle to the store folder. | `check_result` rows, a Bundle file under `FHIR_STORE_DIR` | study |
| POST | `/api/quick/{spot_id}` | The three-question return check. | a quick `visit` | study |
| POST | `/api/upload` | A creek photo. Re-encoded as a new JPEG of at most 1600 pixels, so no metadata survives. | a file under `UPLOAD_DIR`, an `upload` row with a hash of the token | upload; 8 MB at most |
| GET | `/api/photo/{photo_id}` | One uploaded photo with its token. | nothing | read; `?t=` must be the token, or 404 |
| POST | `/api/walk` | A finished video walk's demo record and its follow-up checks, as the Worker stores them; expired rows go on each new store. | a `walk_record` row and a `walk_checks` row | study; the same body cap, follow-up rules, daily cap and time window as the Worker |
| GET | `/api/walk/{record_id}` | One stored walk record until its delete date. | nothing | read |
| GET | `/api/walk/{record_id}/fhir` | One stored walk record's demo Bundle alone, until its delete date. | nothing | read |
| GET | `/api/creeks` | Every creek with a record. | nothing | read |
| GET | `/api/city/{creek_id}` | The analyst's view of one creek. | nothing | read |
| GET | `/api/inaturalist/{creek_id}` | The iNaturalist context line for one creek, from the `inaturalist_cache` table. It never asks iNaturalist itself. | nothing | read |
| GET | `/api/spot/{spot_id}` | One spot's record. | nothing | read |
| GET | `/api/spot/{spot_id}/fhir` | The latest visit at a spot as FHIR. | nothing | none |
| GET | `/api/fhir/Bundle/{visit_id}` | One visit as FHIR. | nothing | none |
| GET | `/api/fhir/validation` | The last validator run. | nothing | none |
| GET | `/api/fhir/referral/{spot_id}` | The ServiceRequest for a pipe worth testing. | nothing | read |
| GET | `/api/fhir/referral/{spot_id}/example-result` | The example laboratory result. | nothing | read |
| GET | `/api/two` | Ours beside theirs. Unlike the Worker, this fetches their sandbox itself, one request a second at most, and keeps what it got for an hour under `SANDBOX_CACHE_DIR`. | a cache file on disk, never in git | none |

`/health`, `/api/skeleton/ping`, `/api/two` and the three FHIR record routes carry no limiter on
the Python API. It serves development and the tests, not the public.
