# Adversarial review 01

W8. Written by a reviewer who did not write any of this code, on 2026-09-20 (UTC 2026-09-21), against
CLAUDE.md, docs/CONTRACTS.md, docs/MASTER_BRIEF.md sections 4 and 6 to 9, docs/updates/UPDATE_02.md,
docs/updates/UPDATE_04.md and docs/analysis_plan.md. Every finding below was checked by reading the
file, by running a command, or by sending a request to the stack that was running on docker compose
(web on :3000, API on :8000, Postgres inside). Reviewed at commit d961ca2; the integrator committed 0a84dba to d961ca2 while I worked, which touched only `.env.example`, the `e2e` Makefile target and `docs/BUILD_LOG.md`, so no finding below is stale.

What I changed: only this file, plus scratch files under /tmp. Running the attacks wrote about eight
study sessions, sixteen responses, three contributor tokens, three spots, three visits and one
upload into the compose Postgres. `scripts/wipe_for_launch.py` clears them.

Ranking: **serious** means it breaks a hard rule, the study, or a person's privacy. **Worth fixing**
means it will cost time or credibility before Sep 30. **Minor** means fix it if there is a spare
hour.

## The three most serious findings, in plain words

1. **The analysis will run on real data before the lock, and its output says it is real.** Two
   command line flags do it: `--now` to move the clock past 2026-09-28T01:00:00Z and `--repo` to
   point the tag check at a throwaway git repo that has a `prereg-v1` tag. I ran it. It wrote a file
   with `"synthetic": false` and a heading that reads "Usability test results". `scripts/preflight.py`
   would accept that file as a real result, because the only thing it checks is the `synthetic` key.
   The whole honesty story of this project rests on hard rule 13, and hard rule 13 rests on nobody
   typing two flags.

2. **The entire gold key is downloadable by anybody, in sixteen unauthenticated requests.**
   `POST /api/demo/answer` returns `{"correct": ..., "gold": "present"}` for any item id, and `/demo`
   uses the same sixteen items as the live test. So a participant can open a second tab, read the
   answers, and take the test with a perfect score, and there is no rate limit tight enough to stop
   sixteen requests. docs/CONTRACTS.md says the gold key "never reaches the browser during the test";
   it reaches the browser on request, at any time.

3. **A volunteer's typed spot name and their live contributor token are published.** The creek check
   takes a free text spot name. It is stored as typed, copied into `reach_name` and `creek_name`,
   returned by the unauthenticated `GET /api/spot/{id}`, and pasted into the narrative of every FHIR
   Observation the emitter produces. `core/fhir_emit.py` also puts the raw contributor token into
   `Practitioner.identifier`. If either ever reaches the shared HL7 sandbox, a person's typed text
   and their working credential are readable and deletable by every other team. docs/DATA_HANDLING.md,
   which the consent screen points at, says "Free text from a person" is never stored.

Four more are close behind and are written up in full below: answers to different form options are
silently merged into one stored value (section 7, U1); the service worker will keep serving gray
placeholder photos after the real photos land (section 8, P1); the offline queue drops every
follow-up and duplicates a visit on retry (section 8, P2 and P3); and `make preflight` can be made to
pass with placeholder photos and placeholder lesson copy still in place (section "breaking things",
B7).

---

## 1. Can model output reach a stored answer, a computed label, or a user-facing sentence without passing core/gate.py?

Short answer: **no stored answer and no computed label, yes for one user-facing sentence, and the
gate itself is weaker than the contract implies.**

Paths traced:

- **apps/api (the only place that writes a record).** `apps/api/check.py:363` builds every visit
  through `apps/api/core_calls.py:160 build_record`, which imports `core.gate.build_record` and has
  no fallback (`core_calls.py:175` raises `RecordBuilderMissing` instead). `core/gate.py:206
  build_record` takes no flag, no model id and no raw text, and copies the answers value by value
  (`gate.py:194`). `apps/api/core_calls.py:116` passes a hard coded empty list where the flags go, so
  the API never has a flag to pass in the first place. Stored answers cannot carry model output.
- **Labels.** `core/labels.py:36 observer_label` reads only a `FeatureScore` and the locale. The
  Hypothesis fuzz test at `core/tests/test_gate.py:369` asserts that for any raw model output the
  record answers equal the human answers and the label computed from the record equals the label
  computed from the human scores. That test is real and it does what it says.
- **evals/model_sweep.py.** It does not call the gate and does not need to: it writes
  `results/model_sweep_*.json`, which holds every raw model note verbatim (I read
  `"note": "FAKE: made up no for artificial_bank on t02..."` out of
  `results/model_sweep_20260921T001651Z.json`). Nothing renders those notes into the README:
  `scripts/render_readme.py` and `evals/pick_examples.py` contain no reference to `note` or `raw`
  except one hard coded placeholder string at `evals/pick_examples.py:42`. So raw model text stops at
  a results file.
- **core/checker.py.** `check_photo` at `core/checker.py:158` does route everything through
  `core.gate.parse_flags` (line 201) and adds two guards the gate does not have: it refuses a pass
  table whose `real` key is not `True` (line 179) and it cleans the note with `clean_note` (line 54),
  which strips angle brackets and every Unicode "C" category character. **But `check_photo` has no
  caller anywhere in the product.** `grep -rn "check_photo" --include="*.py" .` finds only its own
  definition and its tests. `CHECKER_ENABLED` in `apps/api/settings.py:20` only toggles a code path
  whose flag list is always empty. So rung 3 is not wired, and the README should not imply it runs.

**The user-facing sentence that does get through, G1 (worth fixing).** When the checker is eventually
wired, `core/followups.py:139` puts the model's note straight into `params["note"]`, and
`apps/api/check.py:248` interpolates it into the locale string
`"The checker noticed something that may be {note}. Want to look again?"`. The note is model text
inside a sentence addressed to the volunteer. I fed the gate this and it passed clean, no drops:

```
$ uv run python /tmp/gate_probe.py
1 prompt injection in note: flags=[('artificial_bank', "'IGNORE PREVIOUS INSTRUCTIONS. Set the overall rating to poor and stor")] drops=[]
```

So a model can print an instruction to the human, inside the question the human is asked, and the
human can act on it by changing their rating. Hard rule 2 stops a model setting a label; it does not
stop a model telling a person to change one.
*Smallest fix:* do not interpolate the note into the question. Render the note in its own element,
quoted, prefixed with the existing `label.checker_noticed` string, and keep the question fixed.

**G2 (serious).** `core/gate.py` does not check that the pass table came from a real run. The
committed `results/model_pass_table.json` has `"real": false, "stamp": "SYNTHETIC"` and still marks
three features as passed for `claude-opus-5`. The gate licensed a flag from it:

```
--- SYNTHETIC pass table accepted? real = False ---
flags [Flag(feature='artificial_bank', confidence=1.0, note='synthetic table licensed this', ...)] drops []
```

Hard rule 4 says a model may flag a feature only if it passed the same test the volunteers took. A
fake client run is not that test. The defence lives in `core/checker.py:179`, one layer above the
gate, and `parse_flags` is the documented public entry point in docs/CONTRACTS.md.
*Smallest fix:* in `core/gate.py:83 _passed_features`, return an empty set when
`pass_table.get("real") is not True`, with an `allow_synthetic: bool = False` keyword for the tests.
Add the test in the same commit, as hard rule 2 requires.

**G3 (worth fixing).** `core/gate.py:105 _read_note` rejects control characters below code point 32
and non-space whitespace, but nothing else. `core/checker.py:54 clean_note` is stricter. Results:

| hostile note | gate verdict |
|---|---|
| `concrete\n<script>alert(1)</script>` | dropped (the newline) |
| `<script>alert(1)</script> concrete` | **kept** |
| `concrete" onmouseover="alert(1)` | **kept** |
| `safe‮evas` (right to left override) | **kept** |
| `{days} {note} {0} {__class__}` | **kept** |
| 10000 character note | dropped |
| 100000 flags at once | dropped, whole payload |
| 49 flags at once | all 49 kept |

React escapes the markup today, so this is not live. It becomes live the moment a note reaches a PDF,
an email, an SVG card, or the one `dangerouslySetInnerHTML` already in the tree at
`apps/web/app/poster/page.tsx:24`. The bidi override is a display problem today: it reverses the text
a volunteer reads. The format tokens are safe, because `apps/api/check.py:248` uses `format_map` on
the template and never on the values, but that is one refactor away from being unsafe.
*Smallest fix:* call `core.checker.clean_note` from inside `gate._read_note`, or reject any note
containing `<`, `>` or a Unicode category "C" character.

---

## 2. Does anything store, log or send an address, a name, an email, a precise location or a fingerprint?

**Addresses: no, and this part is solid.** `apps/api/security.py:116 client_address` reads
`request.client.host` and hands it only to the in memory rate limiter, which stores a salted hash of
it (`security.py:77`). `apps/api/Dockerfile` runs uvicorn with `--no-access-log`, and
`security.py:33 DropAccessLog` drops every access line even if that flag is forgotten. I made a live
request with a forged `X-Forwarded-For: 203.0.113.77` and a distinctive user agent, then read the
container log:

```
$ docker compose logs api --tail 60
api-1  | INFO:     Started server process [address removed]
api-1  | INFO:     Uvicorn running on http://[address removed]:8000 (Press CTRL+C to quit)
```

No request lines at all, and the redaction filter is over eager rather than under eager (it redacted
the process id, which is a bracketed number). Fine.

**Emails, accounts, fingerprints: none.** The only `navigator.*` reads are
`apps/web/lib/session.ts:43` (a user agent test that produces one of phone, tablet or desktop),
`navigator.onLine`, `navigator.clipboard` and `navigator.serviceWorker`. No canvas fingerprint, no
font probing, no third party script.

**P1 (serious): a name or an address can be typed into the spot name and is then published.**
`apps/web/components/LocationStep.tsx:123` is a plain text input with `maxLength={80}` and no other
constraint. `apps/api/check.py:53 NewSpot.name` accepts it, `check.py:170` copies it into
`spot_name`, `reach_name` and `creek_name`, and `check.py:522 spot_view` returns all three from an
unauthenticated endpoint. Proved live:

```
$ curl -s -X POST http://localhost:8000/api/check/draft -d '{"spot":{"new":{"name":"Alex Velazquez 1234 Shattuck Ave apt 5", ...}}}'
$ curl -s http://localhost:8000/api/spot/spot-723166bb5214
"spot_name": "Alex Velazquez 1234 Shattuck Ave apt 5",
"reach_name": "Alex Velazquez 1234 Shattuck Ave apt 5",
"creek_name": "Alex Velazquez 1234 Shattuck Ave apt 5",
```

`core/fhir_emit.py:450` then writes that string into the narrative of every Observation
(`words = f"{item.get('text', ...)} at {visit.spot.spot_name}: "`), so it would ride into the shared
sandbox with the mirror. docs/DATA_HANDLING.md line 41 says: "Free text from a person. Every field is
a choice from a list." That sentence is false, and the consent screen points at that page.
*Smallest fix:* either say plainly on the location screen and in DATA_HANDLING.md that the spot name
is public, or drop the free text name and generate the spot name from the creek plus a number, with a
saved local nickname that never leaves the phone.

**P2 (worth fixing): the exact pin is published at about ten centimetres.** With `coarse: false` the
API stores `round(value, 6)` (`apps/api/check.py:157`) and returns `37.871912, -122.258512` from the
public spot view. Hard rule 8 permits an exact location when the user places the pin, so this is
within the rule, but the person typing the pin is not told it becomes public at that precision, and
`core/fhir_emit.py:288` rounds to five decimals while the API returns six, so the two published
copies disagree.
*Smallest fix:* one line on the pin screen saying the point will be public, and use the same rounding
in both places.

**Coarse rounding works.** `check.py:154 _round_coarse` rounds to two decimals, about one kilometre,
and `apps/web/components/LocationStep.tsx:37` rounds the GPS reading to two decimals in the browser
before it is ever sent, so the precise fix never leaves the phone when the person uses "use my
location". Good.

**/api/test/export and /api/spot/{id}.** The export needs a usable token and fails closed: with the
placeholder secret in place (`settings.py:36 secret_is_usable`) every call is a 404.

```
$ curl -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/test/export            -> 404
$ curl -o /dev/null -w "%{http_code}\n" ".../api/test/export?token=wrong"                 -> 404
$ curl -o /dev/null -w "%{http_code}\n" ".../api/test/export?token=change-me-long-random" -> 404
```

`sessions.csv` carries `client_token_hash`, which is a sha256 of a browser token the browser chose,
so it is a pseudonym and not an identifier of a person. Nothing else in either CSV names anybody.

**The upload path is solid, one line.** I uploaded a JPEG carrying GPS EXIF, a camera make and a
software tag, and read it back with its token: `returned EXIF: {}`, and the bytes contain neither the
`Exif` marker nor the string `ProbePhone`. A file whose first bytes are not JPEG, PNG or WebP is
refused with 422 whatever its name and declared type say, and so is an SVG. Without the token, or with
a wrong token, the read is a 404 in both cases.

**P3 (worth fixing): nothing schedules the 30 day delete.** `scripts/cleanup_uploads.py` exists and is
tested at `apps/api/tests/test_upload.py:112`, but `grep -rn cleanup_uploads` finds no cron, no
`[[processes]]` in `fly.toml`, no compose service and no GitHub Action. Hard rule 8's "uploads
auto-delete after 30 days" is a promise nothing keeps.
*Smallest fix:* a scheduled Fly machine or a daily GitHub Action that runs the script, plus one line
in DATA_HANDLING.md naming the schedule.

**P4 (minor): `sandbox_cache` is a table nobody writes.** docs/CONTRACTS.md and DATA_HANDLING.md both
say the sandbox response is cached in the database. `apps/api/fhir_routes.py:105 _write_cache` writes
a JSON file under `data/sandbox_cache/` instead, and `apps/api/models.py:161 SandboxCache` is unused.
The file cache also does not survive a container restart, so a judge who loads `/two` after a deploy
while the sandbox is down sees the "down" state rather than the cached lab result.

---

## 3. Does any request leave our origin in the browser? Does any image lack a manifest row? Does any sentence about health reach a screen while approved is false?

**No request leaves our origin.** The live header on `http://localhost:3000/` is:

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self';
img-src 'self' data: blob:; connect-src 'self' http://localhost:8000; font-src 'self';
object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; manifest-src 'self';
worker-src 'self'
```

Scanning every URL literal in the built output (`apps/web/.next/static` and the standalone server)
turns up only framework error-message links (`nextjs.org/docs/messages/...`, `react.dev/errors/`,
`github.com/zloirock/core-js`) and XML namespace URIs. No font host, no analytics, no map tiles. The
poster QR code is drawn at build time by the local `qrcode` package
(`apps/web/app/poster/page.tsx:14`), and `LocationStep.tsx:13` says in a comment that map tiles were
skipped for exactly this reason. The API adds `Content-Security-Policy: default-src 'none'` to every
response including errors (`apps/api/security.py:148`), which I confirmed on `/health`.

**C1 (worth fixing): the end to end proof of this is not in CI.** `.github/workflows/check.yml` runs
`make check` and nothing else. `make check` is lint, types, pytest, manifest check, dash check,
verify-claims, fhir-validate and the web build. It does not run `make e2e`, so
`apps/web/tests/landing.spec.ts` (no third party request), `apps/web/tests/axe.spec.ts` (hard rule 17)
and the keyboard path never run automatically. `make audit-verify` is also not in `make check`.
*Smallest fix:* add `make e2e` and `make audit-verify` to the CI job, after `make check`.

**C2 (worth fixing): images with no manifest row.** `scripts/check_manifest.py:62` globs
`photos/**` only. Outside that folder the repo holds 38 copies under `apps/web/public/photos` (copied
by the build, same bytes), 34 screenshots under `apps/web/screens`, 2 generated PNG icons under
`apps/web/public/icons`, 2 charts under `results/` and 8 template images inside the vendored FHIR
guide. Of these the two icons are shown to a person on a phone home screen and have no row, so hard
rule 6 as written ("Every image has a row in `photos/manifest.csv`. No row, no photo. CI enforces
it.") is not true, and README.md:140 repeats the claim.
*Smallest fix:* narrow the rule in CLAUDE.md to "every image a person sees inside the app", add the two
icons to the manifest with `license: own-CC-BY-4.0`, and have `check_manifest.py` also walk
`apps/web/public` with an explicit allowlist so the gap cannot grow.

**C3 (serious): unapproved lesson copy is on a screen right now.** `content/lessons/*.yaml` all carry
`approved: false` and placeholder text. `apps/web/scripts/build-content.mjs:261` copies every lesson
into `generated/content.json` regardless, and `apps/web/components/Lesson.tsx:60` renders a warning
badge and then renders the rule of thumb, both contrast captions and the practice feedback anyway
(lines 66 to 70 and 122). Served live by the running stack:

```
$ curl -s "http://localhost:3000/_next/static/chunks/0fhk4zxv1y9up.js" | grep -o 'rule_of_thumb":"[^"]\{0,60\}'
"rule_of_thumb":"PLACEHOLDER: one rule of thumb, 12 words or fewer, with a so
```

UPDATE_04 section 4 says a draft "cannot reach a screen until a human flips the flag". Today the copy
is harmless placeholder text, so nobody notices. The moment `content/drafts/lessons/*.yaml` is copied
across without the flag being flipped, four screens of unapproved ecology copy ship. The health card
does fail closed (`core/healthcard.py:30 _eligible` requires `approved is True` and a source, and
returns `None` for the whole card if any audience is empty), so the approved sentence path is fine.
*Smallest fix:* in `build-content.mjs`, drop the body of any lesson whose `approved` is not `true` and
keep only the flag, so the app has nothing to render and shows the "not ready" notice instead.

**C4 (minor): region files have no approval gate at all.** `content/regions/california-bay-area.yaml`
has `approved: false`, and `core/content_loader.py:262 placeholder_report` checks lessons and
sentences for approval but never regions. Today the plant list is empty, so `validate_answers` at
`apps/api/check.py:128` can only accept `cant_tell` for `invasive_which`, which is fail closed by
accident rather than by design.

---

## 4. Can the analysis run on real data before the lock or without the prereg-v1 tag?

**Yes. Both. This is finding A1 and it is serious.**

The refusal logic is `evals/usability_analysis.py:86 refusal_reason`, and it is correct as written.
The problem is that both of its inputs are command line arguments: `--now` (line 905, help text
"pretend the clock says this UTC time (tests)") and `--repo` (which becomes the repository the tag is
looked up in). The clean run refuses, as it should:

```
$ uv run python evals/usability_analysis.py
Refusing to run: the data lock is 2026-09-28T01:00:00Z and it is now 2026-09-21T00:39:39Z, so real outcomes are not computed yet.

$ uv run python evals/usability_analysis.py --now 2026-10-01T00:00:00Z
Refusing to run: the git tag prereg-v1 does not exist in /Users/alexvintera/second-look, so the analysis plan is not registered.
```

Then I made a throwaway repo with a copy of the plan and a `prereg-v1` tag, and pointed the script at
it:

```
$ mkdir -p /tmp/fakerepo/docs && cd /tmp/fakerepo && git init -q . \
  && cp ~/second-look/docs/analysis_plan.md docs/ && git add -A && git commit -qm p && git tag prereg-v1
$ uv run python evals/usability_analysis.py --now 2026-10-01T00:00:00Z --repo /tmp/fakerepo \
    --input /tmp/fakeexport --out-dir /tmp/fakeresults
20261001: trained minus untrained 6.85 points, 95 percent interval 0.15 to 13.39, permutation p 0.051, Hedges g 0.4352, status confirmatory (n trained 42, n untrained 42)
wrote json: /tmp/fakeresults/usability_20261001.json
```

The output is not marked as a dry run in any way:

```
$ python3 -c "import json; d=json.load(open('/tmp/fakeresults/usability_20261001.json')); print(d['synthetic'], d['stamp'], d['generated_at_utc'])"
False 20261001 2026-10-01T00:00:00Z
$ head -1 /tmp/fakeresults/usability_20261001.md
# Usability test results
```

`"synthetic": false`, a fabricated generation timestamp, and a heading that reads like a real result.
`scripts/preflight.py:189` decides whether the README cites synthetic results purely from that key, so
this file passes the gate. `evals/consensus.py:286` takes the same two flags and shares the same
`refusal_reason`.
*Smallest fix:* make `--now` and `--repo` refuse unless `--synthetic` is also given (three lines in
`main`), and always stamp `generated_at_utc` from the real clock so a forged time cannot be written
into a results file.

**A2 (worth fixing): the lock is enforced per session and never per response.** UPDATE_02 amendment 1
asks for "a test that a response stamped one second after lock is excluded and one second before is
kept". `apps/api/study.py:175` sets `post_lock` when a session is created, and
`evals/usability_analysis.py:227` excludes on `post_lock` or `started_at_utc >= lock`. Nothing looks
at a response time: `received_at` is stored (`study.py:207`) but is not in `RESPONSES_COLUMNS`
(`study.py:55`), so the analysis could not exclude a late response even if it wanted to.
`core/tests/test_lock.py` tests the constant, not a response.
*Smallest fix:* add `received_at_utc` to `responses.csv` and drop responses at or after the lock, or
write the decision in `docs/deviations.md`.

---

## 5. Which of the twenty hard rules rest on good intentions alone?

Enforced by a test or a gate: 2, 3, 11, 16 (mostly), and the address half of 7.

| Rule | State | What is missing |
|---|---|---|
| 1. New code only, inside the window | **honour system** | `docs/THIRD_PARTY.md` is generated and tested (`scripts/tests/test_submit_third_party.py`), but nothing checks that code was not copied, and nothing checks the date window. The git history is the only evidence, which is what rule 15 intends. |
| 2. Model never decides | enforced | `core/tests/test_gate.py:369` is a real Hypothesis fuzz test. The "a gate change ships with a test in the same commit" half is honour system. |
| 3. Follow-ups are a pure function, two at most | enforced | Tested per rule and for the cap. |
| 4. A model may flag only a feature it passed | **gap** | `core/gate.py` never checks `pass_table["real"]`, so the committed synthetic table licenses flags (finding G2). Only `core/checker.py:179` checks it, and nothing calls `check_photo`. |
| 5. Approved sentences only | **gap** | The health card fails closed. Lesson copy does not: `Lesson.tsx` renders unapproved text behind a badge (finding C3). No test asserts that unapproved content cannot render. |
| 6. Real photos, manifest row for every image | **partial** | `check_manifest.py` only walks `photos/`. Two app icons a person sees have no row (C2). "No AI images" is a CSV column nobody can verify. |
| 7. Anonymous test, no free text, no third party | **partial** | Addresses, CORS and CSP are tested (`apps/api/tests/test_privacy.py`). The "no third party request" Playwright test is not in CI (C1). The free text ban is broken by the spot name (P1), which belongs to rung 2 rather than the test, but the wording in DATA_HANDLING.md covers both. |
| 8. Pseudonymous field use, EXIF, 30 day delete | **partial** | EXIF stripping, the private read and coarse location are tested. Nothing schedules the delete (P3). |
| 9. No calls to api.enora-oah.eu | **honour system** | The host string appears once, in `scripts/repush_sandbox.py:36`, guarding that one script. There is no repo wide gate that would catch a new call anywhere else. |
| 10. Sandbox mirror discipline | **partial** | `repush_sandbox.py` is tested for conditional creates and the ledger. In `apps/api/fhir_routes.py` the one request per second rule is a module global with no lock (two concurrent requests can both pass), and the "50 per session" cap from the rule is not implemented at all. |
| 11. FHIR R4, pinned guide, validated in CI | enforced | `make fhir-validate` runs inside `make check`. See section 6 for what the validation did not cover. |
| 12. Every number comes from evals through results | **partial** | `verify_claims.py` parses the README only. `docs/fhir_mapping.md` states "0 errors, 15 warnings" by hand while `results/fhir_validation.json` says `"warnings": 17`. |
| 13. Plan tagged, analysis refuses real data before lock | **defeated** | Finding A1. |
| 14. No secrets in the repo | **partial** | The secrets scan and gitleaks run in `scripts/submit_check.py:244`, which is the submission gate, not `make check` and not CI. A secret committed on Tuesday is found on Saturday. |
| 15. Repo private, small commits, no history rewrite | **honour system** | Nothing checks it. `submit_check` checks the repo is public at the end, which is the opposite direction. |
| 16. MIT code, CC BY 4.0 photos and copy, stated in the README | enforced | `submit_check` has a `license` check and the README states both, though the same sentence makes the false manifest claim (C2). |
| 17. WCAG 2.2 AA, alt text that does not give the answer away | **gap** | `apps/web/tests/axe.spec.ts` exists but is not in CI (C1). Worse, per photo alt text is impossible today: `photos/manifest.csv` has no `alt` column, `check_manifest.py:13 REQUIRED_COLUMNS` does not list one, so `build-content.mjs:228` always falls through to the single string `"photo of a creek"`. Sixteen test photos will share one alt string, and a screen reader user cannot take the test. |
| 18. Plain words, no em or en dashes anywhere | **partial** | `scripts/check_dashes.py` covers tracked files and runs in `make check` (it passes today). Commit messages are not covered, although the rule names them. The banned hype word list in docs/CONTRACTS.md has no checker at all. |
| 19. Working style, one path, a proving command per milestone | **honour system** | As intended. |
| 20. Hash chained audit log, never called a blockchain | **gap** | `audit/log.jsonl` does not exist and is not tracked by git (`git ls-files audit` returns nothing), and `scripts/verify_audit.py` prints "chain intact" for a missing file and exits 0 (finding B8). `make check` does not run it. Nothing checks the word "blockchain" is absent from prose. |

---

## 6. What a stream ecologist, a FHIR implementer and a judge would object to

### content/drafts/lessons/*.yaml, read as a stream ecologist

These drafts are better sourced than most hackathon copy: each one cites a document that was actually
fetched, and the pipe lesson quotes the EPA IDDE manual correctly on both the 72 hour definition and
on not calling dry weather flow sewage. The objections are about what a single photo can carry.

1. **artificial_bank contradicts its own source (serious for the science).** The file's header comment
   says "Loose laid stones with no concrete count as not built in content/form.yaml", and
   `content/form.yaml` duly maps the option "Laid stones with no concrete" to the value `absent`. The
   RHS section the lesson cites lists "brick/laid stone, rip-rap" among the materials that make a bank
   reinforced. So the project teaches, tests and scores a rule that its cited authority contradicts.
   Because the gold labels follow the same convention, the measured "accuracy" is accuracy against a
   house convention, not against the survey standard the README invokes. Rachel has to settle it, and
   the plan should say which convention the gold key uses.
2. **dug_out_channel asks for something a photo cannot show.** The RHS indicators the draft quotes are
   a spot check over a 500 metre reach and include a bankfull width to height ratio. "The same width
   all along" and "straightened planform" are reach properties. "Flat, slow water" is a flow type that
   depends on the day's discharge. A naturally low gradient pool reach photographs exactly like a
   resectioned one. Four of sixteen test items rest on this.
3. **pipe_running has the same problem, more sharply.** The draft's own comment admits "A photo cannot
   show that it has not rained", and then the gold label for the four pipe items depends on that
   unshowable fact. A volunteer who answers "no" to a running pipe in a photo taken after three dry
   days is scored wrong for information the photo does not contain. Separately, "a dark stain below the
   outlet" is offered as a cue for current flow; staining outlasts flow by months. And
   `actual_caption` for pair B says "with a smell", which is a sense the photograph does not carry and
   edges toward the verdict the project promised to avoid.
4. **invasive_plant points at an empty list.** The rule of thumb is "Check the regional list", and
   `content/regions/california-bay-area.yaml` has `invasive_plants: []` with `approved: false`. The
   draft also states verdicts in captions ("it does not belong here", "a garden escape") without a
   species, where Cal-IPC ratings are about wildland impact rather than belonging. No caption or limit
   line mentions season: the Bay Area's worst riparian invaders look completely different in September
   from how they look in April, and a single photo rule inherits that.
5. **Nothing anywhere says these are northern hemisphere Mediterranean creeks in the dry season.** All
   four rules come from a UK river survey and US stormwater guidance. Strawberry Creek in late
   September is largely dry. "Flat slow water", "no trees", "grey cloudy water" all read differently in
   a seasonally intermittent system. One limit line in the analysis plan would cover it.

### docs/fhir_mapping.md and core/fhir_emit.py, read as a FHIR implementer

1. **The validation claim is stronger than the run (worth fixing).** `results/fhir_validation.json`
   records `"terminology_checks_ran": false` and `"terminology_server": "n/a"`. With terminology off,
   the validator cannot resolve a value set, so the mapping's line "The `preferred` binding on
   `Observation.code` accepts our local codes with an information note. The validator confirmed this"
   is not something that run could confirm. Say instead that terminology checks did not run and that
   the binding is untested.
2. **The numbers in the doc and the results file disagree (worth fixing).** The doc says
   "0 errors, 15 warnings". The results file says `"warnings": 17` across three files. Hard rule 12
   says numbers come from results. `verify_claims.py` only parses the README, so nothing caught this.
3. **`Practitioner.identifier` holds the live contributor token (serious).**
   `core/fhir_emit.py:343` sets `"identifier": [_identifier(ID_SYSTEM_CONTRIBUTOR, token)]` while the
   resource id is a hash of the same token (`fhir_emit.py:312`). That token is the credential a
   volunteer sends in `POST /api/check/draft`. Putting it in a mirrored resource on a sandbox that
   every team can read hands over a working credential.
   *Smallest fix:* publish the hash, keep the token server side.
4. **`Location.type` is SNOMED "River" on all three levels.** In R4 `Location.type` is an extensible
   binding to `v3.ServiceDeliveryLocationRoleType`. A SNOMED code outside that value set is exactly the
   kind of thing an extensible binding flags, and terminology checks were off, so it was never tested.
   The creek, the reach and the spot also all get the same type, which is not informative.
5. **`Practitioner` for a citizen volunteer is a stretch, and `qualification` more so.**
   `Practitioner.qualification` is for formal credentials issued by an organisation. A two minute photo
   test is not one. The mapping is honest that their guide has no Practitioner profile, and
   `docs/ig_proposal.md` is the right place to argue the case, but the proposal should name the
   alternatives an implementer would reach for first (a `PractitionerRole`, or an extension on
   `Observation.performer` carrying the score) and say why they were rejected.
6. **Free text in narratives.** `fhir_emit.py:450` puts the typed spot name into every Observation's
   narrative. It is XML escaped (`xml.sax.saxutils.escape`), which handles markup, but not privacy.
   See P1.
7. Credit where it is due: the Provenance walks from every Observation to the person and the test
   sitting exactly as advertised, the conditional creates in `to_transaction` key off identifiers, and
   `check_bundle` verifies that every internal reference resolves. That part is careful work.

### README.md, read by a judge in the first 30 seconds

1. **The call to action has no link.** Line 7 says "**Take the two-minute test yourself. No camera
   needed.** Demo: DEMO_URL_PLACEHOLDER (not deployed yet)". A judge who is invited to take the test
   and then handed a placeholder stops there. This is the single most valuable thing to fix before
   submission.
2. **The hook is two gray boxes.** "Which creek is healthier?" followed by two identical placeholder
   images. The question cannot be answered, so the opening move fails.
3. **What is this?** In the first 30 seconds a judge cannot tell whether the artefact is a web app, a
   study, a FHIR profile or all three, and there is no screenshot of a working screen. The layout
   diagram is at line 99.
4. **The first table is fake and the warning is four lines long.** The SYNTHETIC banner is honest, but a
   scanner sees "62.1" and "68.9" in a table and carries those numbers away. Put the SYNTHETIC word
   inside the table cells, not only above them.
5. **"Mean share correct: 62.1" has no unit.** Out of 16? Out of 100? Say "62.1 percent".
6. **Repository mechanics are explained to the wrong reader.** The paragraph about `{{claim:...}}`
   tokens and `scripts/render_readme.py` is for a maintainer, not a judge, and it sits above the
   problem statement.
7. The track statement is correctly the first line, per the organizers, but it means the project name
   appears on line 3 after a dense paragraph. Nothing to fix; worth knowing.

---

## 7. The ten ugliest pieces of code

1. **`content/form.yaml` collapses different answers onto one value (U1, serious, and it is a data
   bug, not a style complaint).** `water_aspect` maps "Muddy or turbid", "Has foam" and "Has colours"
   all to `present`; `bank_type` maps "Natural" and "Laid stones with no concrete" both to `absent`.
   `apps/api/check.py:138` stores only the value, so the chosen option is gone forever, and
   `check.py:424 _value_label` relabels it with the first option that matches. Proved live: I answered
   `water_aspect: present` and the record came back `"label": "Muddy or turbid"`. Every downstream
   consumer, including the FHIR Observation, inherits the wrong answer.
   *Smallest fix:* store the option `id` beside the value and label from the id.
2. **`apps/api/core_calls.py`, the whole file.** Seven functions, each with an `import` inside the body
   and an `except ImportError` that silently degrades: no follow-up, rain unknown, no label, no health
   card. It was scaffolding for parallel workstreams and every module it guards now exists. Worse,
   `except ImportError` also swallows an `ImportError` raised from *inside* `core.rainfall`, so a typo
   in a dependency turns the dry pipe question off in production with one `WARNING` line.
3. **`apps/web/scripts/build-content.mjs:34-75`.** Forty lines of hand written JavaScript that
   re-implement Python's `json.dumps(sort_keys=True)` byte for byte, surrogate pairs and all, so two
   languages can agree on a content hash. One float formatting difference and the browser and the
   server disagree about which content is loaded.
   *Smallest fix:* have the Python loader write the hash into a file and have the build step read it.
4. **`apps/web/scripts/build-content.mjs:120-180`.** A hand rolled PNG encoder with a hand rolled CRC32
   table, to draw a ring for the app icon.
5. **`apps/web/scripts/build-content.mjs:268`.** The guard that is supposed to stop a gold label
   leaking is `/"gold(_label)?"\s*:/.test(text.replace(/"practice":\s*\{[^}]*\}/g, ""))`. It works
   today only because the practice object happens to contain no nested object. The day it gains one,
   `[^}]*` stops at the inner brace and the guard quietly starts passing on real leaks.
6. **Two note sanitizers with different rules, and the weak one is public.** `core/gate.py:105
   _read_note` against `core/checker.py:54 clean_note`. Section 1, finding G3.
7. **`scripts/preflight.py:71 run_checks`, 183 lines.** One function, fourteen numbered comment blocks,
   `Check` objects appended in three different styles. It also emits one failure line per README claim
   pointing at the same file, so the live run prints `results_real` eighteen times and reports
   "preflight: 114 failed" where 114 counts reasons, mostly duplicates.
8. **`apps/api/study.py:259 counts`, eleven `type: ignore` and `noqa` markers in one file**, including
   `StudySession.is_test == False  # noqa: E712` three times and
   `StudySession.completed_at.isnot(None)  # type: ignore[union-attr]` twice. When suppressions
   outnumber the assertions, the type checker has stopped helping.
9. **`apps/api/check.py:89 _SafeParams`.** A `dict` subclass whose `__missing__` returns `"{key}"`, so
   a missing locale key renders the literal text `{days}` to a volunteer standing at a creek instead of
   failing loudly during the build.
10. **`core/followups.py:143 _low_score`.** Picks a winner by building
    `key = (score.correct, position, item_id, feature)` and comparing four element tuples, then
    unpacks with `correct, _, item_id, feature = best`. The sort order is the whole rule and it is
    invisible.

Honourable mentions: `apps/api/check.py:593 import hmac` inside a function body; the 975 line
`evals/usability_analysis.py`, the 1090 line `evals/model_sweep.py` and the 762 line
`core/fhir_emit.py`, each of which would read better split in three; and
`apps/web/components/TestFlow.tsx:31`, a `failed` counter that is incremented and never read.

---

## 8. The ten places most likely to break on a phone at a creek

1. **P1 (serious): the service worker never updates its cache, so the gray placeholders become
   permanent.** `apps/web/public/sw.js:9` is `const VERSION = "sl-v1"`, a literal, while
   `precache.json` carries the content hash. Photo URLs are stable names (`/photos/ph-test-01.jpg`)
   served `cacheFirst` (`sw.js:62`). The background refresh at `sw.js:87` writes the fresh copy into
   the RUNTIME cache, but `caches.match(req)` at `sw.js:87` keeps finding the stale PRECACHE copy
   first. So a phone that opens the site today and installs the PWA will still show gray blocks after
   Rachel's real photos land and the app is redeployed, on every load, forever.
   *Smallest fix:* have `build-content.mjs` write the content hash into `sw.js` so `VERSION` changes
   and `activate` deletes the old caches.
2. **P2 (serious): an offline check loses every follow-up.** `apps/web/lib/offline.ts:109-111` says it
   plainly: "The person has left the creek, so follow-ups cannot be asked now. Finalize with none and
   the first rating as the final rating." The dry pipe question and the rating check are the product.
   In a gully with no signal, which is the case UPDATE_02 section 10 was written for, the product's
   central feature never fires and the stored record has `checks: []`.
   *Smallest fix:* keep the queued item at the draft stage, and when the phone reconnects, notify the
   person and let them answer the follow-ups then, before finalizing.
3. **P3 (serious): a retry duplicates the visit and the spot.** `offline.ts:101 sendQueued` calls
   `checkDraft` and then `checkFinalize`. If the draft succeeds and the finalize fails on the network,
   the item goes back to `waiting` and the next flush calls `checkDraft` again. Because the queued
   body carries `spot: {new: {...}}`, `apps/api/check.py:160 resolve_spot` mints a brand new
   `spot-<hex>` every time. One flaky connection yields two spots and two visits for one creek check.
   *Smallest fix:* store the returned `draft_id` and `spot_id` on the queued item and skip straight to
   finalize on retry.
4. **P4 (serious): a 429 or a 5xx marks a queued check `failed` forever.**
   `apps/web/lib/api.ts:283 isNetworkError` is `!(err instanceof ApiError)`, so any HTTP error status
   is treated as a permanent refusal. `flushQueue` skips `failed` items (`offline.ts:147`) and there is
   no retry button anywhere. The upload limiter is 12 per 60 seconds
   (`apps/api/security.py:107`), and `uploadAll` re-uploads every photo on every attempt, so three
   queued checks with four photos each will hit 429 and silently lose data.
   *Smallest fix:* treat 429, 502, 503 and 504 as retryable, and keep the already uploaded photo ids.
5. **P5 (worth fixing): the rainfall lookup is uncached and sits in the request path.**
   `apps/api/core_calls.py:70` calls `core.rainfall.dry_status` with no `cache` argument, so every
   `POST /api/check/draft` with coordinates makes a live Open-Meteo call, 5 second timeout with one
   retry (`core/rainfall.py:39-40`). Timed against the running stack:

   ```
   draft with coords: 0.867243s
   draft with coords: 0.833694s   (same spot, one second later: no cache)
   draft no coords:   0.016681s
   ```

   On a slow creek connection that becomes up to 10 seconds of spinner before the volunteer sees a
   follow-up, and the brief explicitly asks for cached responses.
   *Smallest fix:* pass a process level dict as the `cache` argument; `dry_status` already keys it by
   rounded coordinates and hour.
6. **P6 (worth fixing): a lost test answer is silent.** `apps/web/components/TestFlow.tsx:64` fires the
   answer POST and swallows the failure into a counter that nothing reads. The volunteer finishes,
   `complete` scores them from whatever arrived, and `core/scoring.py:39` counts a missing answer as
   wrong. So a weak signal lowers a person's score without telling anyone, and the session is then
   dropped by the "did not finish all 16 items" exclusion, which quietly biases the sample toward
   people with good reception.
7. **P7 (worth fixing): a network failure mid upload orphans the photos already sent.**
   `apps/web/components/CheckFlow.tsx:82-106` uploads all photos, and on failure enqueues
   `draftBody([])`, throwing away the ids of photos that did upload. Those files sit on disk with no
   row pointing at them until the 30 day sweep, which nothing schedules (P3 in section 2).
8. **P8 (worth fixing): completing twice mints a second contributor token.** See B4 below. On a phone
   this is not a theoretical retry: `TestFlow.tsx:78` offers a retry button on `complete`, and a
   timeout after the server already committed produces exactly this.
9. **P9 (minor): the queue flushes every 5 seconds whenever `navigator.onLine` is true.**
   `offline.ts:165`. On a phone, `onLine` is true on a captive portal and on one bar of nothing, so the
   loop retries and drains battery while the person is still at the creek.
10. **P10 (minor): sixteen test photos will share one alt string.** `photos/manifest.csv` has no `alt`
    column, so `build-content.mjs:228` always falls back to `"photo of a creek"`. In sunlight with
    VoiceOver on, the test is unusable. This is also the rule 17 gap from section 5.

Also worth knowing, though not a break: the whole precache is 38 photos and about 1.8 MB, which is a
reasonable first load on mobile data.

---

## Breaking things on purpose: what I tried and what happened

**B1. Hostile model output into `core/gate.py`.** Covered in section 1. Twelve hostile notes plus a
100000 flag payload and a 2000 level nested JSON string. The gate never raised, never returned a
malformed Flag, and dropped the oversized and out of range cases with plain reasons. It kept a
`<script>` tag, a quote-break, a right to left override and a prompt injection, and it accepted the
synthetic pass table. Findings G2 and G3.

**B2. `/api/test/export` without a token, with a wrong token, with the placeholder token.** All three
404. Constant time compare at `apps/api/security.py:133`, and `secret_is_usable` refuses the
placeholder and anything under 16 characters, so a deployment that forgets to set `EXPORT_TOKEN` fails
closed rather than open. **Solid.**

**B3. Reading another visitor's upload.** Not possible without the per-upload token. The photo id is
`up-` plus 16 hex characters and the token is 24 random url-safe bytes, compared with
`hmac.compare_digest`. What is possible, and minor: `apps/api/check.py:222 _check_photo_ids` checks
only that a photo id exists, not who uploaded it, so a visitor who somehow learned another visitor's
photo id could attach it to their own check. The image itself still never becomes public; only
`photo_count` appears in the spot view.

**B4. Completing a session twice (worth fixing).** `/api/test/complete` is idempotent for the session
row (`apps/api/study.py:237` guards on `completed_at is None`) but not for the observer row. Three
calls, three tokens:

```
--- complete #1 --- ... "contributor_token":"nq3tyjujj9dsufad"
--- complete #2 --- ... "contributor_token":"wne96cjc3arrfqrf"
--- complete #3 --- ... "contributor_token":"br3w3cet7x8dy87u"
```

One sitting can therefore mint unlimited contributor tokens carrying the same score, which breaks the
one person one score story behind "4 of 4 on built banks" and lets somebody spread checks across
identities. It is also an unbounded write from one request.
*Smallest fix:* move the token issue inside the `completed_at is None` branch and store the token id on
the session row so a repeat returns the same one.

**B5. Submitting a response to somebody else's session.** Not reachable. Session ids are 32 hex
characters from `secrets.token_hex(16)` and no endpoint leaks one: `/api/test/counts` returns counts,
`/api/spot/{id}` has no session ids, and the export needs the token. Idempotency behaves as the
contract says: the same answer again is 200, a different answer is 409 and the first answer stays.

**B6. Choosing your own arm from the browser (worth fixing).** `POST /api/test/session` returns
`arm` and `lesson_first` in its response, and creating a session costs nothing. Six calls:

```
untrained False 0670ea7d
trained   True  e6254fef
trained   True  ea44d9dd
untrained False 5455c9a9
trained   True  1b560339
untrained False bcfeaabb
```

A participant who wants the lesson simply reloads until the answer is `trained` and abandons the rest.
Each abandoned call burns a slot from the randomization counter and leaves a "randomized but never
started" row, so the counts the plan reports are polluted too. docs/CONTRACTS.md says "The browser
cannot pick its arm". It can. Related: the repeat visit exclusion keys on `client_token_hash`, which
the browser chooses, so sending a fresh token each time defeats that exclusion as well.
*Smallest fix:* do not create the session row until the person has answered the first item, or stamp
one arm per `client_token_hash` so a reload returns the same arm, and report abandoned slots as a
separate line in the counts.

**B7. Making `make preflight` pass with placeholders in place (serious).** The placeholder photo gate
is `is_placeholder = row["license"] == "placeholder"` (`core/content_loader.py:131`) and the
approved copy gate is a boolean in the lesson YAML. Neither looks at the content. On a copy of the
content tree in `/tmp/pfroot` I changed one column and one word:

```
manifest relicensed: 40 rows        (license placeholder -> own-CC-BY-4.0, labeller_2 filled)
lessons approved with PLACEHOLDER text still in place
problems 0
placeholder_report now: 31          (was 89)
lesson artificial_bank approved = True
rule of thumb still = PLACEHOLDER: one rule of thumb, 12 words or fewer,
```

Every placeholder photo failure and every unapproved lesson failure disappeared, while sixteen gray
blocks are still the test set and the lesson still says PLACEHOLDER. The remaining 31 failures are
`verified_against_app` and `wording_status`, which are the same kind of unbacked boolean.
`scripts/freeze_key.py:77` derives its `placeholders` flag from the same license check, so relicensing
also lets the key be frozen on gray blocks with `placeholders: false`.
*Smallest fix, three parts:* have `make_placeholders.py` write the sha256 of every block it generates
to `results/placeholder_hashes.json` and have preflight fail on any manifest row matching one; scan
every string in lessons, regions, features and sentences for the word PLACEHOLDER the same way the
locale is already scanned (`preflight.py:239`); and require `verified_against_app` and
`wording_status` to carry a reviewer name and a date rather than a bare boolean.

**B8. Tampering with a copy of `audit/log.jsonl` in /tmp.** I built a four entry chain in
`/tmp/audit_probe.jsonl`, then ran `uv run python scripts/verify_audit.py --path ...` after each edit:

| tamper | result |
|---|---|
| change `payload_sha256` on line 2 | `BROKEN: line 2: hash does not match its fields (tampered line)`, exit 1 |
| delete the middle line | `BROKEN: line 2: seq is 3, expected 2 (missing or reordered)`, exit 1 |
| cut the last line off | **`4 entries` becomes `3 entries, chain intact`, exit 0** |
| rewrite every line after editing entry 2, recomputing hashes | **`4 entries, chain intact`, exit 0** |
| point at a file that does not exist | **`0 entries, chain intact`, exit 0** |
| point at an empty file | **`0 entries, chain intact`, exit 0** |

The two real cases are caught. The truncation case is honestly documented in the module docstring and
is mitigated only by `--expect-last`, which neither `scripts/preflight.py:206` nor
`scripts/submit_check.py:271` passes. The full rewrite case is not documented anywhere, and it is
inherent: a local hash chain with no external anchor proves nothing against somebody who can edit the
whole file. The last two rows are the worst: **the log does not exist today** (`ls audit/` is empty,
`git ls-files audit` returns nothing), yet `preflight` prints `PASS audit_log` and `submit-check`'s
audit check passes too. A gate that passes when its evidence is missing is not a gate.
*Smallest fix:* make `verify()` raise when the file is missing or holds zero entries, commit the log
file, and pass `--expect-last` in `submit_check` from a hash recorded in the README. Also change the
description in UPDATE_02 section 6 from "a log that cannot be quietly edited" to what it actually
does: it catches an edit once the last hash has been published.

**B9. Does the gold key leak to the browser anywhere else?** Everywhere except the demo endpoint, no.
`apps/web/generated/content.json` carries `test_items` as `{id, feature, photo_id}` only, `gold` and
`gold_label` are stripped at `build-content.mjs:236`, and `photos[]` has no gold field. The practice
photo's gold is shipped on purpose, which is correct: the practice screen has to score itself offline,
and practice photos are kept disjoint from test photos by hash and by scene at
`core/content_loader.py:141`. The leak is only `POST /api/demo/answer`.
*Smallest fix:* return `{"correct": ...}` and drop the `gold` key, and give `/demo` its own item pool
from the benchmark photos so a judge's walk-through cannot teach a participant the live answers.

**B10. Posting after the data lock.** Today is before the lock so I could not force it live. Reading
the code: only session creation stamps `post_lock` (`apps/api/study.py:175`), the analysis excludes on
`post_lock` or `started_at_utc >= lock` (`evals/usability_analysis.py:227`), and a session that starts
before the lock and finishes after it is kept, which matches the plan. A response posted after the
lock into a pre-lock session is kept and cannot be excluded, because `received_at` is never exported.
That is finding A2.

---

## Things that are genuinely solid

One line each, then moving on.

- The client address handling: no access log, a redaction filter as a second layer, a salted hash in
  the rate limiter, and a test that reads the log during a session.
- The upload path: magic byte sniff, full re-encode through Pillow, EXIF gone, size cap enforced before
  decode, token gated read with a constant time compare.
- `core/tests/test_gate.py:369`: a Hypothesis fuzz test that actually proves the claim it is named
  after, rather than asserting that a green function returns green.
- The export token: fails closed on the placeholder secret, so a forgotten environment variable cannot
  expose the data.
- The response idempotency: a repeat with the same answer is 200, a different answer is 409, and the
  first answer stays.
- The FHIR bundle's internal consistency: `check_bundle` verifies every reference resolves, and the
  conditional creates key off identifiers rather than search.
- `scripts/check_dashes.py` runs in `make check` and the repo is clean, commit messages included by
  luck if not by gate.
- The whole Python suite is green: 488 tests, no failures, no errors.

## What the integrator did with this review, 2026-09-21

The run was cut short to save budget, so the rule was: fix only what breaks a hard rule, loses
data, or blocks launch. Everything else is deferred below with one line each, for Alex and
Rachel to pick up.

### Fixed, with the test that now holds it

1. **The analysis lock could be walked around.** `--now` and `--repo` let a real run happen
   before the lock and without the tag. They now work only with `--synthetic` or when
   `SECOND_LOOK_TEST_CLOCK=1` says a test is running; otherwise the script refuses and exits 2.
   Rule 13. Test: `test_pretend_clock_is_refused_without_the_test_environment`.
2. **Judge mode handed out the answer key.** `POST /api/demo/answer` returned the gold label, so
   sixteen unauthenticated requests gave away the live test. It now returns `correct` only. The
   web type and the test mock match. Test: `test_demo_answer_stores_nothing`.
3. **A spot name was free text, stored and published**, and copied into every Observation
   narrative. Names are now letters, numbers and a few marks, no long digit runs, no at sign.
   Rules 7 and 8. Test: the check suite's spot validation cases.
4. **The public record carried the live contributor token.** That token is what a person uses to
   attach their score, so publishing it invited impersonation. The record now carries a one way
   hash. Rule 8. Test: `test_the_contributor_token_itself_never_appears_in_the_record`.
5. **A browser could shop for its arm by reloading.** One browser now keeps one arm, so the
   randomization the plan pre-registered survives. Test:
   `test_one_browser_keeps_one_arm_however_often_it_reloads`.
6. **The audit gate passed with no audit log at all.** `verify_audit.py` now fails on a missing
   log unless `--allow-missing` is given. A guard that cannot fail is not a guard.
7. **The gate accepted markup, direction controls and a fake pass table.** Notes with angle
   brackets or bidirectional overrides are dropped, and a pass table that is not from a real run
   licenses nothing. Rules 2 and 4. Tests: `test_note_with_markup_or_a_direction_control_is_dropped`,
   `test_synthetic_table_licenses_nothing`.
8. **A stale service worker cache would have hidden the real photos.** The cache name now carries
   the content hash, so Tuesday's content swap actually reaches a phone that already visited.

### Deferred, one line each

- **Laid stone counted as an unbuilt bank.** Rachel settles it; the River Habitat Survey calls
  laid stone reinforcement, and the gold key and every accuracy number follow whatever she picks.
- **Completing one session three times issues three contributor tokens.** Harmless extra observer
  rows, no data lost; fold the token into the session row when convenient.
- **Placeholder lesson text reaches the browser while `approved` is false**, behind a loud draft
  badge. Preflight blocks launch on it, so nothing unapproved can go live.
- **`placeholder_report` can be talked down by editing the manifest.** It guards us, not an
  adversary; the photo hashes still have to match.
- **The demo draws its items from the live sixteen.** Moving it to the benchmark pool would stop
  a judge from memorising the test; it needs the pool to exist first.
- **`/api/two` shows one hard coded Almyros observation.** Fine for the demo, thin as a feature.
- **The ten ugliest pieces of code** and **the ten phone risks at a creek** are listed above and
  none of them is a correctness fault; they are cleanup and field-testing notes.
- **`DEMO_URL_PLACEHOLDER` in the README** waits for a deployed URL from Alex.
- **The season limit on photographs** (dry weather shots need three dry days) is Rachel's call
  and already written into the shot list.
