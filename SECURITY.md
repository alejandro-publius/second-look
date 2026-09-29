# Security and privacy

What Second Look keeps, what it never keeps, how the secrets and the locks work, and how to tell
us about a problem. The full list of fields is `docs/DATA_HANDLING.md`, which the privacy page
points to; this page follows it and adds the security side. Every route, with its lock, is in
`docs/API.md`.

## What we keep

- **The two-minute test.** A sitting (`session`): a random id, the arm, the item order, the consent
  version, the content and build hashes, the times, seconds per lesson screen, a hash of a random
  browser token, a coarse device class, the coarse source of the link, a test flag and the warm-up
  choice. Its answers (`response`): yes, no or can't tell per photo, with the first choice, the
  count of changes and timing.
- **The second look (part 2, `/t2`),** for a person who is offered it after the score. A sitting
  (`part2_session`): a random id, the id of the test sitting it follows and that sitting's arm,
  the part 2 arm, the photo order, the times, whether the offer was declined, the same hash of
  the browser token and a test flag. Its answers (`part2_response`): the first and the final
  answer per photo, whether the checker's question was shown, keep or change, with timing.
- **A kept score,** only when the person ticks "Keep my score": a random contributor token, the
  four scores and the test date (`observer`). It is not linked to the sitting.
- **Creek checks.** The spot (a coarse point about a kilometre wide, unless the person placed the
  pin), the answers as coded values from pick lists, the language the questions were shown in,
  the ratings, the follow-up questions asked and their answers, what the rainfall lookup said,
  the contributor token if the person chose to carry their score, and the FHIR Bundle of the
  visit. The public FHIR record names the person only by a hash of that token
  (`core/tests/test_fhir_emit.py::test_the_contributor_token_itself_never_appears_in_the_record`).
- **Photos people upload,** with their camera metadata cut out, readable only with the one token
  handed to the uploader, and deleted after 30 days. Each photo has a row: its id, a hash of that
  token, the file type, the size and the time. On the live site no code deletes that row yet, so
  it stays after the photo is gone.
- **One laboratory record** copied from the OneAquaHealth sandbox for `/two`.
- **A finished video walk's demo record,** so its link opens on any device: the walk's id, the
  answers as coded values, the time, its FHIR Bundle, tagged as a demo, which states the language
  the questions were shown in, and the follow-up checks the rules asked with their coded answers,
  in tables of their own.
  No token, no position, no free text. At most 200 a day, deleted after 30 days, never counted
  and never mirrored (`POST /api/walk`, `docs/DATA_HANDLING.md`).
- **On the phone,** in the browser's own storage for this site: the random browser token, the
  contributor token, saved spots, the ids of the open test sitting and of the open second look,
  the language chosen for the questions (`sl.check_lang`), checks and walks that wait to be sent,
  and a walk's answers while it is being made. `docs/DATA_HANDLING.md` names each key.

## What we never keep

- Names, emails, phone numbers, accounts or passwords. There are no accounts.
- Internet addresses. The Python API drops uvicorn's access log and removes anything that looks
  like an address from every other log line; a test runs a whole sitting and reads every log line
  (`apps/api/tests/test_privacy.py::test_full_session_leaves_no_client_address_in_any_log_line`).
  Our Worker code writes no address anywhere. Cloudflare keeps its own short lived edge records,
  which we do not read; the consent screen says so.
- Free text from a person, except the name typed for a new spot, which is public. Every other
  answer is a choice from a list.
- Photo metadata. The Python API re-encodes an upload as a new JPEG; the Worker, which cannot
  re-encode, cuts the EXIF, XMP, ICC, comment and text segments out of JPEG, PNG and WebP files.
  The Worker e2e uploads a JPEG with a GPS tag and checks it is gone (`worker/test/e2e.mjs`,
  "quick check and upload"); `apps/api/tests/test_upload.py` checks the Python side.
- Third party scripts, analytics, fonts or fingerprinting. The site's Content Security Policy lets
  the browser load scripts, styles, fonts and images from our own origin only (an image may also be
  one the page made itself) and connect to our own origin only (`apps/web/security-headers.mjs`).
  The Python API's answers carry `default-src 'none'`.
- Anything from judge mode (`/demo`). A video walk's answers stay on the phone until the walk is
  finished; only its demo record, above, is ever sent.

## Secrets

`QA_KEY` and `EXPORT_TOKEN` are Worker secrets; `ANTHROPIC_API_KEY` lives only in an ignored `.env`
on one Mac. No value is in the repository: `.env.example` is tracked and `.env` is not, and
`make secrets`, part of `make check`, runs gitleaks over the history and scans every file git would
commit. The pre-commit hooks run the same scans on each commit (`DEPLOY.md`). Both servers compare a
secret in constant time and treat one shorter than 16 characters as not set. The Python API also
treats the placeholder in `.env.example` as not set; the Worker does not check for it.

- **The QA key** does one thing: a sitting started with the `x-qa-key` header set to it is marked
  as a test, so a check of the live site never lands in the data
  (`apps/api/tests/test_study.py::test_qa_key_header_marks_a_test_session`). It cannot read
  anyone's answers. A wrong key is not an error; the sitting is simply real, so
  `apps/web/scripts/live-check.mjs` reads the public counts before and after and fails if they
  moved. The web app can carry a QA key of its own (`NEXT_PUBLIC_QA_KEY`) only in a dry-run build;
  the launch build leaves it empty.
- **The export token** opens `/api/test/export`, the anonymous CSV files of the test and, on the
  live site, of part 2. Without it the route answers 404, as if it did not exist
  (`apps/api/tests/test_study.py::test_export_needs_the_token_and_returns_the_exact_schema`,
  `apps/api/tests/test_study.py::test_export_holds_no_identifier_columns`).
- **The model key** is read by the eval scripts alone. It is never exported in the shell that runs
  a coding agent, and `make judge-check` and `make demo-offline` remove it before they start.

## The lock

The data lock is 2026-09-28T01:00:00Z, one constant in `core/lock.py` and in `worker/src/index.ts`.

- **Judge mode's answer route is shut until then.** Before the lock, `POST /api/demo/answer`
  answers 403 on both servers, because sixteen answers would be the live test's key. After it,
  the route says only whether an answer was right, never the gold label, and stores nothing
  (`apps/api/tests/test_study.py::test_demo_answer_is_shut_before_the_lock`, and the Worker e2e
  section "judge mode shut before the lock").
- **The answer key never ships to a browser.** After every build, `apps/web/scripts/check-bundle.mjs`
  reads every file the site serves and fails the build if one carries a gold label.
- **The analysis refuses real data before the lock,** and also without the git tag `prereg-v1` on
  its pinned commit, or when `docs/analysis_plan.md` differs from the tagged, hashed plan. No option
  or variable stands in for the clock or the repository
  (`evals/tests/test_usability_refusal.py::test_no_option_or_variable_fakes_the_clock_or_the_repo`).

## Rate limits

The Python API limits each client address over a short sliding window, per kind of route (the
numbers are in `docs/API.md`). The counter lives in process memory only, keyed by a salted hash of
the address, and is gone when the process stops
(`apps/api/tests/test_privacy.py::test_too_many_requests_get_429_then_recover`).

The deployed Worker has no rate limit, on purpose. A Worker has no shared memory, so counting per
visitor would mean holding something that identifies them, which the anonymous test forbids. In
its place: a hidden form field that catches simple bots, sittings under 40 seconds left out of the
analysis, one arm per browser, and Cloudflare's own edge protection. If abuse turns up, the answer
is Cloudflare's rate limiting rules at the edge, which never hand an address to our code.

## The model and the shared sandbox

- A vision model never writes a record. Its output becomes a flag through `core/gate.py` or is
  dropped, and a flag can only make one follow-up question eligible, for a feature that model
  passed on the same test as the people. `WRITEUP.md` explains the gate.
- The MCP server (`apps/mcp/`) is read only, runs locally, and refuses any id that is not one plain
  name, so a call cannot reach another route (`docs/MCP.md`).
- Their sandbox is written by conditional create with our tag on everything, plus one conditional
  update on our own Library entry, matched by our own identifier. It is deleted from only by an id
  our own ledger recorded: never by search, never with `$expunge`
  (`scripts/tests/test_repush_sandbox.py::test_delete_refuses_unknown_ids_searches_and_operations`).
  We make no call to OneAquaHealth's closed API, and the mirror refuses its host by name
  (`scripts/tests/test_repush_sandbox.py::test_push_refuses_the_forbidden_host`).
- `audit/log.jsonl` is a hash-chained audit log of the moments that matter. It holds hashes, not
  data; `scripts/verify_audit.py` checks the chain.

## Known gaps

- The Worker's routes are open to anyone, with no rate limit, as above.
- Without `ALLOWED_ORIGIN` set, the Worker answers any origin for CORS. The site reaches it on its
  own origin, and nothing it serves needs a login, so CORS is not what protects it.
- On the Python API, `/health`, `/api/skeleton/ping`, `/api/two` and the three FHIR record routes
  (`/api/spot/{spot_id}/fhir`, `/api/fhir/Bundle/{visit_id}`, `/api/fhir/validation`) carry no
  rate limit; it serves development and the tests, not the public.

## Reporting a problem

Please use GitHub's private vulnerability report on this repository: the Security tab, then
"Report a vulnerability". If that is not open to you, open an issue that says only that you found a
security or privacy problem and asks for a private way to send it. Please leave the details out of
the issue. We will reply there, and once the problem is fixed, the commit that fixes it will say
what was wrong.
