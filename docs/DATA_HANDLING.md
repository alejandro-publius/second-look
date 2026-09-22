# Data handling

What our code stores, what it never stores, what the hosts log on their own, and how long
anything lives. Plain words, because the consent screen points here. Hard rules 7 and 8 in
CLAUDE.md are the source; docs/CONTRACTS.md has the table columns.

## What our code stores

Usability test (the two-minute test at `/t`):

- `session`: a random session id, the arm (trained or untrained), the block id, the item order,
  the consent text version, the content hash and build hash, when consent was given, when the
  test started and finished, seconds spent on each lesson screen, a hash of a random browser
  token, a coarse device class (phone, tablet or desktop), a QA flag, the coarse source label
  from the link (poster, chat, friends, creek_group or other), whether the hidden form field was
  filled, whether the session started after data lock, the optional yes or no to "Have you ever
  assessed a stream before?", and the warm-up choice.
- `response`: session id, item id, the answer (yes, no or can't tell), the reaction time in
  milliseconds, the position in the test, and when it arrived.
- `observer`: only when the person ticks "Keep my score for creek visits": a random 16 character
  contributor token, the four scores as "k of 4", and the test date. This row is never linked to
  the session id.

Creek check (rung 2, `/check`):

- `spot`, `visit`, `check_result`: the spot (creek, reach, spot names; coordinates only if the
  person placed the pin, otherwise a coarse point), the answers to the form items as coded
  values from pick lists, the first and final rating, which follow-up rules ran and the answer,
  and the contributor token if the person chose to carry their score.
- `upload`: the photo bytes after EXIF stripping, a per-upload token, and the upload time.
- `sandbox_cache`: copies of public Observations fetched from the OneAquaHealth sandbox, so the
  two-observer screen still works when the sandbox is down.

Export: `GET /api/test/export?token=...` gives `sessions.csv` and `responses.csv` with the
columns listed in docs/CONTRACTS.md. Neither file has a name, an address, a token or a time
more precise than the second.

## What our code never stores

- Names, emails, phone numbers, accounts or passwords. There are no accounts.
- IP addresses or client addresses. The API runs with access logs off in production and a test
  fails if an address appears in the server log.
- Free text from a person. Every field is a choice from a list. The official app's "Which ones?"
  free text became a pick list plus "Not sure".
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
  records: the client internet address, the requested path, the user agent, the time, the
  response code and the country its network works out from the address. On the free plan these
  are aggregate analytics plus short-lived operational logs; we cannot switch them off and we do
  not read, export or join them to anything of ours.
- Cloudflare's Workers observability is on for the API, which keeps recent request traces for a
  short retention window. Those traces hold the path and the response code. Our own code writes
  no address into them, and we do not log request bodies.
- D1 holds the study tables. Workers KV holds creek check photos after downsizing and EXIF
  stripping. Both sit in the same Cloudflare account.
- GitHub hosts the code, the daily database backup as a private artifact, and the anonymous
  response table after publication; it logs downloads in aggregate.

The consent screen says: "Cloudflare, which serves this site, keeps its own short-lived
connection records, which include internet addresses. We do not." That sentence must stay true;
if we change hosts, change both this file and the consent text.

## Retention

- Uploads: deleted after 30 days by `scripts/cleanup_uploads.py`. A visitor never sees another
  visitor's upload; each is served only with the token returned to the uploader.
- Study tables (`session`, `response`): kept until the analysis is published, then the
  anonymous response table (the export CSVs) is published with the results and the raw tables
  are dropped. Dry-run rows are wiped at launch by `scripts/wipe_for_launch.py`, which writes
  the wipe into docs/deviations.md and the audit log.
- `observer` rows: a score expires after 90 days and the person retakes the test. Expired rows
  are shown as expired, not used.
- Creek records (`spot`, `visit`, `check_result`): kept; they are the point of the product.
  Our own FHIR store is the source of truth; the sandbox mirror is a copy we can rebuild.
- `sandbox_cache`: replaced on each successful fetch; never committed to git.

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

The raw database is backed up once a day by `.github/workflows/backup.yml`, which runs
`wrangler d1 export` against the `second-look` database and keeps the dump as a private GitHub
Actions artifact. The token it uses is scoped to D1 read on this one account and nothing else.
`scripts/backup_db.sh` still covers the compose stack. Nobody computes outcomes from a backup. The only code that computes outcomes is
`evals/usability_analysis.py`, which refuses to run before data lock (2026-09-28T01:00:00Z)
and refuses to run without the `prereg-v1` tag. A restore drill was run once before launch;
docs/internal/BUILD_LOG.md records it.

## The audit log

`audit/log.jsonl` is a hash-chained audit log of the moments that matter: plan tagged, key
frozen, launch wipe, model pass table written, data lock, records written, sandbox pushes.
It holds hashes, not data. `scripts/verify_audit.py` checks the chain. It is an audit log, not
a blockchain.
