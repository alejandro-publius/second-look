# Data handling

What our code stores, what it never stores, what the hosts log on their own, and how long
anything lives. Plain words, because the consent screen points here. Hard rules 7 and 8 in
CLAUDE.md are the source; docs/CONTRACTS.md has the table columns.

## What our code stores

The study has two windows. The first ran until the first data lock, 2026-09-28T01:00:00Z, under
`docs/analysis_plan.md` (tag `prereg-v1`) and `docs/analysis_plan_v2.md` (tag `prereg-v2`). The
second wave runs from 2026-09-30T04:00:00Z to the second lock, 2026-10-03T04:00:00Z, under
`docs/analysis_plan_v3.md` (tag `prereg-v3`). Both windows write the same tables and the same
fields, listed below; the second wave stores nothing the first did not (plan v3 item 9). Which
window a sitting belongs to is read from its start time, not from a field of its own.

Usability test (the two-minute test at `/t`):

- `session`: a random session id, the arm (trained or untrained), the block id, the item order,
  the consent text version, the content hash and build hash, when consent was given, when the
  test started and finished, seconds spent on each lesson screen, a hash of a random browser
  token, a coarse device class (phone, tablet or desktop), a QA flag, the coarse source label
  from the link (poster, chat, friends, creek_group, panel or other), whether the hidden form field was
  filled, whether the session started after the first data lock (`post_lock`, read against
  2026-09-28T01:00:00Z, so every second wave sitting carries it), the optional yes or no to "Have you ever
  assessed a stream before?", the warm-up choice, and how many answers the phone had given that
  the server did not hold when the test ended (`unsent_count`).
- `response`: session id, item id, the answer (yes, no or can't tell), the reaction time in
  milliseconds, the position in the test, when it arrived, the first choice made on that photo,
  the time to that first choice in milliseconds, and how many times the choice changed before
  Next.
- `observer`: only when the person ticks "Keep my score for creek visits": a random 16 character
  contributor token, the four scores as "k of 4", and the test date. This row is never linked to
  the session id.
- `arm_slot` and `counter`: the order of the groups, written before launch, and how far along it
  the test is. Nothing about a person.

Part 2, the assisted second look (`/t2`, offered on the score screen of the test; on the live
Worker only, the Python API has no part 2):

- `part2_session`: one row for each test sitting that was offered the second look and chose. It
  holds a random id of its own, the id of the part 1 session it follows, that session's arm, the
  part 2 arm (assisted or unassisted), the block id, the order of the eight photos, when the
  offer was answered, whether it was declined, when part 2 started and finished, a second copy
  of the same hash of the random browser token, a QA flag, and whether it began after the first
  data lock (the same `post_lock` mark, which every second wave sitting carries).
  A row for "No thanks" has no arm, no block and no photo order.
- `part2_response`: for each of the eight photos, the part 2 id, the item id, the position, the
  first answer, the final answer, whether the checker's question was shown, the choice made
  after it (keep or change, empty when no question was shown), the time to the first answer and
  to the final answer in milliseconds, and when the first answer arrived.
- `part2_slot` and `part2_counter`: the order of the part 2 groups, written before part 2
  opened, and how far along it each part 1 arm is. Nothing about a person.
- Nothing else, as `docs/analysis_plan_v2.md` item 11 says. Part 2 joins a person's two sittings
  by the session id. It stays anonymous: neither row holds a name, an address or free text.

Creek check (rung 2, `/check`):

- `spot`: a spot id, the creek, reach and spot names with their ids, the coordinates (only if the
  person placed the pin, otherwise a coarse point), whether the point is coarse, and when the
  spot was made.
- `visit`: a visit id, the spot, the kind (a full check or a quick check), the time of the
  check and the time it was finished, the answers to the form items as coded values from pick
  lists, the language the questions were shown in (one of the six the check offers, English when
  none was sent, empty for a quick check), the first and final rating, the ids of the photos
  sent with it, the follow-up questions the rules chose, what the rainfall lookup said for the
  spot (dry, wet or unknown, the dry days and the millimetres), the software version, and the
  contributor token if the person chose to carry their score.
- `check_result`: for each follow-up question that was asked, the rule, the question as it was
  worded, the coded answer, and the rule's kind and the values it was asked with.
- `fhir_bundle`: the FHIR Bundle of each finished visit, built from the rows above. It states
  the language too, and names the person only by a hash of the contributor token.
- `upload`: on the live site the photo itself sits in Workers KV, with its EXIF and other
  metadata cut out. Its row holds a photo id, a hash of the one token that opens the photo, the
  file type, the size in bytes and the upload time. The token itself is handed to the uploader
  and is not stored. The Python API keeps the photo as a file on private disk and the same row
  with the file's name.
- `skeleton_ping`: empty on the live site, where no route writes it. On the Python API
  `/api/skeleton/ping` writes a fixed note and the time, to prove the database works. Nothing
  from a person.
- `sandbox_cache`: copies of public Observations fetched from the OneAquaHealth sandbox, so the
  two-observer screen still works when the sandbox is down.
- `inaturalist_cache`: per creek, a short summary of public iNaturalist observations near its
  spots (a plant name, a count, the latest date and a link), with the time it was fetched. No
  observer's name, photo or exact position is stored.

Video walks (`/walk`, a creek from your desk; UPDATE_30 section 1 items 2 and 3):

- While a walk is being made, its answers stay on the phone, in the browser's IndexedDB beside
  the creek check's offline queue, keyed by the walk's id, so Back, a reload or a closed tab
  opens it where it was. Start again deletes them.
- `walk_record`: once the walk is finished, the phone sends it to our store as a demo record, so
  its link opens on any device. A row holds the walk's id, the answers as coded values from the
  form's lists, the time the walk was finished, the time it was stored, its delete date and its
  FHIR Bundle, tagged as a demo on every resource. No contributor token, no position, no photo,
  no free text and nothing about the browser. The phone also sends the language the questions
  were shown in (`language`, one of the six the check offers, English when none was sent). The
  Bundle states it; the row has no column of its own for it. The route refuses a body over 4096
  bytes, any field but those three, the two below and `language`, an answer the form does not
  allow, and a time more than 5 minutes ahead or 7 days old, and it takes at most 200 walk
  records a day on the whole server.
- `walk_checks`: the follow-up questions the creek check's rules asked on the walk's answers and
  what the person answered, as a creek check keeps its own in `check_result`, and the final
  rating. The phone sends the answers (`followup_answers`) and the rating (`final_rating`); the
  store runs the rules itself and refuses an answer to a question it did not ask or an answer
  the question does not take. A row holds the rule, the question as the locale words it, the
  coded answer and the rating, one row per walk record, stored with it and deleted with it.
- A walk record is never counted: it is in no study table, it is not a spot or a visit, so no
  creek's numbers, no `/city?creek=` view and no count include it. It is never sent to
  OneAquaHealth's sandbox: the mirror reads visit Bundles only and refuses anything with the
  demo tag. It shows only on `/spot?id=<its id>` and on `/city?walk=<walk>&record=<its id>`, the
  links the walk page gives.

On the phone, in the browser's own storage for this site. None of it is sent anywhere but as
the fields named above:

- localStorage `sl_client_token`: the random browser token. Only its hash ever leaves the phone.
- localStorage `sl_contributor_token`: the contributor token, after "Keep my score".
- localStorage `sl_saved_spots`: the ids and names of up to 20 spots the person checked.
- localStorage `sl_open_session`: the id of the last test sitting and the lesson card it was
  on, so a reload finds it and the second look knows which test it follows. It is removed only
  when a reload cannot get the sitting from the server, because the server no longer knows it
  or cannot be reached; the next sitting writes over it.
- localStorage `sl_open_part2`: the ids of the open second look and of the test sitting it
  follows, kept the same way. No code removes it; the next second look writes over it.
- localStorage `sl.check_lang`: the language chosen for the questions, so the next check or walk
  opens in it. It leaves the phone only as the `language` of a check or a walk that is sent.
  Where the browser refuses storage, the choice lasts until the page is closed.
- sessionStorage `sl_src` and `sl_landing_guess`: the coarse source label from the link and the
  pick on the first page, until the tab is closed. The pick is sent as the warm-up choice only
  after consent.
- IndexedDB `second-look`: creek checks and finished walks that wait to be sent, with their
  downsized photos, and each walk's answers and language while it is being made. A creek check
  that waited here stays after it is sent: its photos are removed, but its spot, its answers,
  its first rating, its language and the contributor token, if it had one, stay until the
  person clears the site's data. No code removes it.
- The service worker's cache: copies of this site's own pages, scripts and photos, so the site
  opens offline. It holds no answer and nothing from `/api`.

Who else gets a spot's position: Open-Meteo, for the rainfall lookup behind the dry pipe
question, at 4 decimals; and iNaturalist, from the daily job on the Mac, which asks for sightings
near each spot of a creek whose region has an approved plant list, at the precision the spot is
stored (5 decimals for a placed pin, 2 otherwise). Neither gets a name, a token or an answer.

Export: `GET /api/test/export?token=...` gives `sessions.csv` and `responses.csv` with the
columns listed in docs/CONTRACTS.md. On the live site it gives two more, `part2_sessions.csv`
and `part2_responses.csv`, with the columns in `worker/src/part2.ts`. No file has a name, an
address or a token. Each sessions file has the hash of the random browser token, and
`part2_sessions.csv` has the id of the part 1 session it follows. Clock times are to the second;
reaction times are in milliseconds.

## What our code never stores

- Names, emails, phone numbers, accounts or passwords. There are no accounts.
- IP addresses or client addresses. The API runs with access logs off in production and a test
  fails if an address appears in the server log.
- Free text from a person, with one exception: the name typed for a new spot when its pin is
  placed. That name is stored and shown on the spot's public page, so it must not be a person's
  name. Every other field is a choice from a list. The official app's "Which ones?" free text
  became a pick list plus "Not sure".
- Precise location, unless the person places the pin themselves. Otherwise the spot is coarse.
- Photo EXIF (camera, time, GPS). Uploads and our own photos are stripped before storing;
  `scripts/ingest_photos.py` proves it with a test.
- Browser fingerprints, third-party analytics, fonts or scripts. The page's Content Security
  Policy allows our own origin only, so the browser enforces it too.
- Anything from `/demo`. Judge mode stores nothing.
- Raw data from OneAquaHealth's closed systems. We only fetch their public sandbox.

## What the hosts log on their own

We do not control the hosting providers' own logs. Plainly:

- Cloudflare Pages serves the web pages and Cloudflare Workers runs the API (Update 09
  section 2). Cloudflare sits in front of every request, so it sees and keeps its own edge
  records: the client internet address, the requested address with its query string, the user
  agent, the time, the response code and the country its network works out from the address. So
  if a research panel adds its own identifiers to its link, the first page request carries them
  to Cloudflare's edge, before any of our code runs; the page then removes them from the address. On the free plan these
  are aggregate analytics plus short-lived operational logs; we cannot switch them off and we do
  not read, export or join them to anything of ours.
- Cloudflare's Workers observability is on for the API. Its logs hold each request's method and
  full address, query string included, so they carry a photo's one-time token (`?t=`) and, on the
  export route, the export token, with the response code and the timing, for up to 7 days. Our own
  code writes no client address into them, and we do not log request bodies.
- Cloudflare sends Network Error Logging headers with every page (`report-to` and `nel`, to
  `a.nel.cloudflare.com`). A browser may then report a failed request to Cloudflare, and the report
  names the address that failed. It is Cloudflare's own setting; we never see the reports.
- D1 holds the study tables. Workers KV holds creek check photos after downsizing and EXIF
  stripping. Both sit in the same Cloudflare account.
- GitHub hosts the code and, after publication, the anonymous response table; it logs downloads
  in aggregate. It holds no copy of the database: the daily backup stays on Alex's Mac (see
  Backups).

The consent screen says: "Cloudflare, which serves this site, keeps its own short-lived
connection records, which include internet addresses. We do not." That sentence must stay true;
if we change hosts, change both this file and the consent text.

## Retention

- Uploads: on the live site the photo is deleted 30 days after it was stored, by the store's
  own expiry (Workers KV, `worker/src/uploads.ts`). Its `upload` row is not deleted by any code
  today, so the id, the token hash, the file type, the size and the time stay after the photo
  is gone, and so does the photo's id in its visit. They open nothing then. On the Python API
  `scripts/cleanup_uploads.py` deletes the files and their rows after 30 days, each time it is
  run. A visitor never sees another visitor's upload; each is served only with the token
  returned to the uploader.
- Part 2 tables (`part2_session`, `part2_response`): no code deletes them. They are kept as
  `session` and `response` are. `docs/analysis_plan_v2.md` item 10 says the anonymous part 2
  response table is published; when the raw part 2 tables are dropped is not written down yet.
- Study tables (`session`, `response`): kept until the analysis is published, then the
  anonymous response table (the export CSVs) is published with the results and the raw tables
  are dropped. Dry-run rows are wiped at launch by `scripts/wipe_for_launch.py`, which writes
  the wipe into docs/deviations.md and the audit log.
- The second wave's sittings sit in the same four tables as the first wave's, and are kept and
  published the same way: `docs/analysis_plan_v3.md` item 8 publishes the anonymous response
  tables as they stand at the second lock, with the results, whatever they show. The first
  wave's rows are not wiped when the second wave opens; the second wave's analysis leaves them
  out by their start time (plan v3 item 4), and the two waves are never pooled.
- `observer` rows: a score expires after 90 days and the person retakes the test. Expired rows
  are shown as expired, not used.
- Creek records (`spot`, `visit`, `check_result`): kept; they are the point of the product.
  Our own FHIR store is the source of truth; the sandbox mirror is a copy we can rebuild.
- `sandbox_cache`: replaced on each successful fetch; never committed to git.
- `inaturalist_cache`: replaced on each successful daily fetch; never committed to git.
- `walk_record`: deleted 30 days after it is stored. Its delete date is written on the row when it
  is stored, and the API never serves a row past it. On the live site the Worker deletes every
  row past its date once a day, at 04:17 UTC (the cron in `worker/wrangler.jsonc`), and again
  whenever a new walk is stored; the Python API deletes them whenever a new walk is stored. A
  daily backup taken before that keeps a row until the backup itself is deleted (see Backups).
- `walk_checks`: deleted with its walk record, in the same step, by both servers.
- A walk's answers on the phone: in the browser until Start again, or until the person clears
  the site's data. They are never sent anywhere before the walk is finished.
- Everything else on the phone: until the person clears the site's data, but for the two
  sessionStorage keys, which go when the tab is closed.

## The rate limit, and why the deployed API has none

The Python API limits requests per client address over a short window. The counter lives in
process memory only, is never written to disk, to the database or to a log, and is gone when the
process restarts. That is still true of the compose stack and of local runs.

**The deployed Worker has no rate limit at all, on purpose.** A Worker has no shared process
memory, so the only ways to count per visitor are to key on the client address (which would mean
holding an address, even briefly, which rule 7 forbids) or to put a counter in D1 or a Durable
Object keyed by something that identifies the visitor. Neither can be done cleanly without
storing what we promised not to store, so we do not do it. What is left:

- The hidden form field on the consent screen catches simple bots. A session that fills it is
  still created, so the bot does not learn it was caught, and it is excluded from analysis.
- Sessions completed in under 40 seconds are excluded, which is in the pre-registered plan.
- One browser keeps one arm, and only the first completed session from a browser token counts.
- Cloudflare's own edge protection sits in front of everything and is not ours to configure away.

If abuse turns up during the week, the answer is Cloudflare's own rate limiting rules at the
edge, which never hand an address to our code, and a line in docs/deviations.md.

## Backups

The raw database is backed up once a day on Alex's Mac, not on GitHub. The launchd job
`com.secondlook.backup` (`DEPLOY.md`, Jobs on the Mac) runs `scripts/backup_d1.sh` at 21:00, or
when the Mac wakes if it slept through that time. The script runs `wrangler d1 export` against the
`second-look` database with the wrangler login already on the Mac, so no token is written down,
and puts the dump in `~/second-look-backups/`. That folder is outside the repo, only its owner can
read it, and it keeps the newest 30 dumps (`BACKUP_KEEP`). No dump goes to git or to GitHub.
`scripts/backup_db.sh` still covers the compose stack.

`.github/workflows/backup.yml` can make the same export on GitHub, but it runs only when someone
starts it by hand, and nobody has: the two secrets it needs were never added, and its only two
runs, scheduled on Sep 21 and 22, failed. It would keep the dump as a GitHub Actions artifact. On
a public repository anyone signed in to GitHub can download those, and this one turns public on
Oct 3. So the dump is kept out of Actions artifacts there: the workflow's job runs only while the
repository is private, and on a public one it is skipped. An artifact made before the flip would
turn public with it, so none should be made; on Sep 25 there were none.

Nobody computes outcomes from a backup before a lock. The only code that computes outcomes is
`evals/usability_analysis.py` and `evals/assist_analysis.py`, which refuse to run before the
first data lock (2026-09-28T01:00:00Z) and refuse to run without the `prereg-v1` and `prereg-v2`
tags, and `evals/wave2_analysis.py`, which calls those two on the second wave's window and
refuses to run before the second lock (2026-10-03T04:00:00Z) or without the `prereg-v3` tag. At
each lock the lock job (`make lock-analysis` at the first, `make lock-analysis-2` at the second,
both `scripts/lock_analysis.py`) takes one more backup on this Mac and exports the study tables
from it (`scripts/study_export.py`, the same files the export route gives), so the one
pre-registered run of each wave reads exactly the snapshot that is kept. That export stays
outside the repo: in `data/export`, which git ignores, and in a copy next to the backup in
`~/second-look-backups/`. A restore drill was run once before launch; the team's working notes (BUILD LOG)
records it.

## The audit log

`audit/log.jsonl` is a hash-chained audit log of the moments that matter: plan tagged, key
frozen, launch wipe, model pass table written, data lock, records written, sandbox pushes.
It holds hashes, not data. `scripts/verify_audit.py` checks the chain. It is an audit log, not
a blockchain.
