# Engineering challenges: how Second Look was built, the hard parts

Second Look gives a creek volunteer a two-minute photo test, stores their score per feature with
every observation they make, and lets a vision model ask one follow-up question only where it
passed the same test. This page is for someone who wants to know what was hard to build and how
each part is proved. Every measured number on it comes from a file in `results/` and is checked by
`scripts/verify_claims.py` in `make check`. Each part names the files that do the work and the
test that fails if it breaks. The decisions behind them are in `docs/adr/`.

## 1. The model never decides

**What was hard.** A vision model's output is text we do not control. It can be malformed, name a
feature that does not exist, be confident about a feature it is bad at, or carry markup meant to
steer what comes next. We wanted the model's help without letting it decide anything that is
stored.

**What we did.** All model output goes through one function, `parse_flags` in `core/gate.py`. It
turns any input into a list of `Flag` objects or drops each candidate with a reason in plain
words, and it never raises. A flag survives only for a feature the model passed in the committed
pass table, with a finite confidence, a short note with no line breaks, markup or text direction
controls, and a region made of fractions. A flood of candidates is dropped whole. A flag can do one
thing: make one follow-up question eligible in `core/followups.py`, which is a pure function of
the answers, the weather, the person's score and the flags, and asks two questions at most.
`build_record`, the only way a record is made, has no parameter that could carry a flag, a model
id or model text.

On the footage run, the gate
dropped <!--v:results/footage_latest.json#/gate/dropped-->29<!--/v-->
of <!--v:results/footage_latest.json#/gate/candidates-->64<!--/v--> candidate flags, every one for a feature
that model had not passed, and kept <!--v:results/footage_latest.json#/gate/kept-->35<!--/v-->.

**Proof.** `core/tests/test_gate.py::test_fuzz_model_output_never_reaches_answers_or_labels`,
`core/tests/test_gate.py::test_build_record_signature_carries_human_inputs_only`,
`core/tests/test_harden_gate_properties.py::test_the_gate_never_raises_and_leaves_its_inputs_as_they_were`,
`core/tests/test_harden_followups_properties.py::test_the_selector_runs_with_http_and_the_model_client_patched_to_raise`.

## 2. A model speaks only where it passed the people's test

**What was hard.** "The model is good at this" has to mean something we can check. A model can be
strong on built banks and weak on pipes, and a table of passes made by a fake client must never
let a real flag through.

**What we did.** Each model takes the same 16 photos as the volunteers, three times, through
`evals/model_sweep.py`. It passes a feature only when it gets all four of that feature's photos
right in at least two of the three runs. The result is a committed file,
`results/model_pass_table.json`, that says `"real": true` only after a paid run. `core/checker.py`
does not even ask the model about a feature it did not pass, and the gate drops such a flag again.
A table from the fake client licenses nothing.

**Proof.** `core/tests/test_checker.py::test_unpassed_feature_returns_nothing_even_when_the_model_is_confident`,
`core/tests/test_checker.py::test_synthetic_pass_table_never_licenses_a_flag_by_default`,
`core/tests/test_harden_gate_properties.py::test_the_committed_pass_table_licenses_only_what_it_marks_passed`.

## 3. Two languages, one answer: the ports proved equal

**What was hard.** The tested code is Python. The live site runs on a Cloudflare Worker with a D1
database, and a Python Worker could not reach D1: D1 is a prepared statement binding, not a
database connection our Python models can use (`docs/notes/hosting.md`). So the site needed the
same functions in TypeScript, and two copies of the same logic drift. Small things differ between
the languages too: Python's `round()` rounds an exact half to the even number and JavaScript's
`toFixed` rounds it up, and Python's random numbers cannot be reproduced in JavaScript.

**What we did.** Python stays the reference. `evals/golden_vectors.py` runs the Python functions on
chosen inputs and writes their outputs to `worker/golden/`: the follow-up selector, the labels, the
health card, the pin guards, the city functions, the region placement, the FHIR emitter and the
hash and rounding helpers. The TypeScript in `worker/src/core/` must reproduce every output
exactly: <!--v:results/test_counts.json#/worker_golden/cases-->282<!--/v--> cases
in <!--v:results/test_counts.json#/worker_golden/files-->9<!--/v--> files, replayed
by <!--v:results/test_counts.json#/worker_golden/node_tests-->20<!--/v--> tests. `worker/src/core/pyround.ts`
rounds the way Python does. Randomization is not ported at all: `scripts/seed_arms.py` writes
`core/allocator.py`'s own sequence into a D1 table and the Worker takes the next slot. The Bundles
the TypeScript emitter writes go through the HL7 validator with the Python ones.

**Proof.** `make worker-check`, which fails when the golden files or `worker/src/content.json` no
longer match what the Python writes, then runs `worker/test/golden.test.ts`;
`evals/tests/test_golden_vectors.py`; `results/fhir_validation.json`,
with <!--v:results/fhir_validation.json#/errors-->0<!--/v--> errors
over <!--v:results/fhir_validation.json#/files_validated-->17<!--/v--> records.

## 4. The answer key stays out of the web bundle

**What was hard.** The test's value depends on nobody seeing the answers first. On 2026-09-22 the
video walks imported the Worker's full content file into page code, and the gold answers shipped
to every browser inside the site's own script files. Nothing failed, because nothing looked.

**What we did.** The content the browser gets is written without the gold labels, and no web file
may import the Worker's full content. After every build, `apps/web/scripts/check-bundle.mjs` reads
every file the site serves and fails the build if one carries a gold label. Judge mode, which does
give feedback per answer, is shut until the data lock and even then says only right or wrong.

**Proof.** `apps/web/scripts/check-bundle.mjs` in `make web-build`;
`scripts/tests/test_web_static.py::test_the_ports_content_that_browsers_get_has_no_gold_key`,
`scripts/tests/test_web_static.py::test_no_web_file_imports_the_workers_full_content`,
`apps/api/tests/test_study.py::test_demo_answer_is_shut_before_the_lock`.

## 5. A mirror on a shared sandbox that deletes nothing by search

**What was hard.** OneAquaHealth's FHIR sandbox is shared: anyone can write there and anyone can
delete. We had to put our records there without ever touching anyone else's, and put them back
when they vanish.

**What we did.** `scripts/repush_sandbox.py` sends each visit as a transaction of conditional
creates, with our tag on every resource, one request a second. Every id the server creates goes
into `fhir/sandbox_ledger.jsonl`. A delete names one id, which must be in the ledger; there is no
delete by search and no `$expunge`. The one update is on our own Library entry, matched by our own
identifier, so it can only ever reach our resource. Only visit Bundles are sent: a demo walk, a
referral or an example is refused by shape. The mirror refuses OneAquaHealth's closed API by name.
A launchd job re-pushes every day that their sandbox answers, and the conditional creates make
that a no-op for what is still there.

**Proof.** `scripts/tests/test_repush_sandbox.py::test_delete_refuses_unknown_ids_searches_and_operations`,
`scripts/tests/test_repush_sandbox.py::test_delete_only_an_id_from_the_ledger`,
`scripts/tests/test_repush_sandbox.py::test_a_demo_walk_record_is_never_mirrored`,
`scripts/tests/test_repush_sandbox.py::test_push_waits_one_second_between_bundles_and_records_matches`.

## 6. A pre-registration that the code enforces

**What was hard.** An analysis plan means something only if it was fixed before the data and the
analysis cannot quietly run early. A review found that test flags could run the analysis on real
data before the lock (findings F06 to F08).

**What we did.** `docs/analysis_plan.md` is tagged `prereg-v1`; its commit and SHA-256 are pinned in
`evals/usability_analysis.py` and `docs/notes/plan_hash.md`. The data lock is one constant,
`core/lock.py`. The analysis refuses real data before the lock, without the tag, when the plan
differs from the tagged one, or when the tag has moved. It reads the real clock and this repository:
no option and no environment variable stands in for either. A synthetic run reads only a folder
marked as generated, never the real export. Changes after the tag go in `docs/deviations.md`.

**Proof.** `evals/tests/test_usability_refusal.py::test_no_option_or_variable_fakes_the_clock_or_the_repo`,
`evals/tests/test_usability_refusal.py::test_a_moved_tag_with_the_same_plan_is_refused`,
`evals/tests/test_usability_refusal.py::test_refuses_when_the_plan_differs_from_the_tag`,
`core/tests/test_lock.py`.

## 7. The enum bug that made a paid run measure our YAML

**What was hard.** The first paid run sent the models an answer tool whose allowed values were read
from YAML. Unquoted `yes` and `no` are booleans in YAML, so the models were told the answer must be
`true`, `false` or `"cant_tell"`. They answered `true`,
and <!--v:results/model_sweep_20260924T030451Z.json#/counts/malformed-->73<!--/v-->
of <!--v:results/model_sweep_20260924T030451Z.json#/counts/answers-->144<!--/v--> answers were counted as
malformed. That run measured our config, not the models. Batches also sat in the queue for hours.

**What we did.** The values are quoted, and a test pins them to the three strings. The test double
for the model SDK now refuses what the real SDK refuses, so a test cannot pass on a request the API
would reject. `EVALS_SYNC=1` makes the same calls directly at the full price, with the cost cap
counted at that price. The run was done again: <!--v:results/model_sweep_20260924T031128Z.json#/counts/malformed-->0<!--/v-->
of <!--v:results/model_sweep_20260924T031128Z.json#/counts/answers-->144<!--/v--> answers malformed. Both runs
stay in `results/`.

**Proof.** `evals/tests/test_model_sweep.py::test_the_answer_tool_allows_exactly_the_three_words_as_strings`,
`evals/tests/test_model_sweep.py::test_a_direct_run_is_estimated_at_twice_the_batch_price`.

## 8. Their sandbox's name went away

**What was hard.** `/two` shows one of our Observations beside a laboratory Observation from their
sandbox. On 2026-09-23 the Worker's fetch started failing, while the Mac still reached the
sandbox, which made it look like a block on Cloudflare. Logging the Worker's status showed HTTP 530
with code 1016, Cloudflare's error for a name it cannot resolve, and a lookup at their own name
server showed the cause: `sandbox.hl7europe.eu` no longer existed there, and the Mac had only an
old cached answer.

**What we did.** The Worker stopped fetching their record live. `scripts/cache_their_records.py`
fetches it on the Mac once a day through launchd, with one read only request, and stores it in D1
with the time it was fetched. The Worker shows that copy and says when it was fetched; with no copy,
the page says so and shows our record alone. The script and the Worker compute the same cache key,
and a failed fetch stores nothing, so the last good copy stays. The day their name resolves again,
the job fills the cache with no change to the code.

**Proof.** `scripts/tests/test_cache_their_records.py::test_the_worker_reads_the_same_query_and_the_same_key_expression`,
`scripts/tests/test_cache_their_records.py::test_a_failed_fetch_stores_nothing`, `worker/src/two.ts`.

## 9. Early Hints and smaller photos

**What was hard.** The landing page opens with two creek photos: the warm-up question "Which creek
is healthier?". Cloudflare Pages had been turning the pages' preload tags into Early Hints, so the
photos started loading before the page arrived. Once the project gained its `/api` Functions,
Pages stopped doing that, and the first screen on a slow phone got much slower. The photos were
also large JPEGs.

**What we did.** The Link headers are written by us now, into `apps/web/public/_headers`, from the
same definition the page uses for its own preload tags (`apps/web/security-headers.mjs`), and
`apps/web/scripts/check-preloads.mjs` fails the build if the two disagree. Then the two photos got
AVIF and WebP copies at several widths, same picture and same crop. Each copy has a manifest row
tracing it to its source's SHA-256, and `scripts/check_manifest.py` checks that it is the same
picture and carries no metadata. Only image bytes changed, logged as a deviation.

Measured on the same throttled phone profile at a pixel ratio of 2, without Early Hints, the photo
bytes on the first screen went
from <!--v:results/warmup_photos.json#/runs/before/dpr/2/median_photo_bytes-->1459038<!--/v-->
to <!--v:results/warmup_photos.json#/runs/after/dpr/2/median_photo_bytes-->253409<!--/v-->, and the median load time
from <!--v:results/warmup_photos.json#/runs/before/dpr/2/median_load_ms-->8445<!--/v--> ms
to <!--v:results/warmup_photos.json#/runs/after/dpr/2/median_load_ms-->2504<!--/v--> ms
(`results/warmup_photos.json`, written by `apps/web/scripts/first-screen.mjs`).

**Proof.** `scripts/tests/test_web_headers.py::test_a_photo_with_smaller_copies_preloads_its_avif_set_and_not_the_jpeg`,
`scripts/tests/test_web_headers.py::test_the_preload_asks_for_exactly_what_the_page_shows`,
`scripts/tests/test_web_headers.py::test_a_copy_made_from_another_version_of_its_photo_fails_the_build`.

## 10. Photo metadata out, without an image library

**What was hard.** A creek photo from a phone carries GPS and the camera's name. The Python API
re-encodes every upload with Pillow, which drops all of that, but a Worker cannot re-encode an
image.

**What we did.** `worker/src/uploads.ts` reads the real type from the first bytes, caps the size, and
cuts the metadata segments out of the file: EXIF, XMP, ICC and comments from a JPEG, the text,
time and EXIF chunks from a PNG, the EXIF and XMP chunks from a WebP. The picture's own bytes are
copied as they are. A JPEG is walked marker by marker through every scan, so metadata between
progressive scans goes too, and nothing after its end marker is kept, where phones put a second
image with its own EXIF; a JPEG that cannot be walked is refused, not copied. A review on Sep 23
found the first version missed those shapes (REVIEW_02 F01), and the fix came on Sep 24. The photo lives in Workers KV with a 30 day expiry, so the deletion promise
needs no job to keep it, and it is served only with the one token given to the uploader.

**Proof.** The Worker e2e section "quick check and upload" in `worker/test/e2e.mjs` uploads a JPEG
with a GPS tag and checks the tag is gone; `worker/test/golden.test.ts` runs the cut on a JPEG with
metadata before the picture, after the end marker, between two scans and after a fill byte, and
on three broken ones it must refuse; `apps/api/tests/test_upload.py::test_upload_strips_exif_downsizes_and_serves_only_with_the_token`.

## 11. A mock that refuses what the servers refuse

**What was hard.** The web app's browser tests run against a mock API. A mock that accepted
anything hid two real bugs: the creek check sent the feelings answer in a shape both servers
refuse, and it sent `changed` where both servers accept only `change`. Anyone who answered those
questions could not send their check, and every test was green.

**What we did.** Both bugs were fixed in the page. `apps/web/tests/mock-api.mjs` now refuses what
the servers refuse, and the spec asserts the exact shapes the servers validate.

**Proof.** `apps/web/tests/check.spec.ts`, which checks the feelings entries and the `change`
answer the page sends, against `apps/web/tests/mock-api.mjs`.

## How the pieces are checked

`make check` runs all of it: lint and types, the Python tests, the image manifest, the dash and
reading age checks, the diagrams, the claims in the README and these docs, the Worker's golden
vectors, the HL7 validator, the web build with the bundle and preload checks, and the design check.
The counts behind each suite are in `results/test_counts.json` (`make test-counts`).
