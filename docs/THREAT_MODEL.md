# Threat model

What in Second Look is worth attacking, who might try, what each of them could do, and what
stops it. Each defence names the test that fails if it breaks. Where nothing stops an attack,
this page says so. It covers the live site and its Worker, the Python API, this repository and
our copy in OneAquaHealth's sandbox. It does not cover Cloudflare's or GitHub's own security, or
a stolen laptop. `SECURITY.md` says what we keep and how to report a problem;
`docs/DATA_HANDLING.md` lists every field.

## Assets

| Asset | Where it lives | Why it matters |
|---|---|---|
| The answer key | `content/test_items.yaml`, hashed in `results/key_hash.json`; the Worker holds it to score | Whoever has it can score 16 of 16 and carry a false score into every later observation, and the study measures nothing |
| The study data | the Worker's D1 database: sittings, answers, times, a hash of a browser token | The pre-registered result is only as good as these rows |
| The contributor tokens | D1, in plain form, and on the person's phone | A token carries a person's score into their creek checks |
| The sandbox mirror | our resources in OneAquaHealth's shared FHIR sandbox, and `fhir/sandbox_ledger.jsonl` | It is how our records reach their world; a wrong delete could hit someone else's data |
| The pass table | `results/model_pass_table.json` | It decides which features each model may flag |
| The QA key and the export token | Worker secrets, and `.env` files that git ignores | The QA key marks a sitting as a test; the export token opens the anonymous export |
| Uploaded photos | the Worker's KV store, for 30 days | A phone photo can carry the place it was taken in its metadata |

## Who might attack

- **A bored participant.** Opens the public link, wants a high score or wants to see what breaks.
  Has a browser and maybe a script, no inside knowledge.
- **A competitor.** Another hackathon team or someone who wants our numbers to look bad. Can read
  the repository once it opens on Sep 30, and can write to the shared sandbox, which is open to
  anyone.
- **A curious judge.** Reads the code, opens the browser's developer tools, tries the routes the
  code names, and checks whether the numbers are real.
- **A model.** Two kinds: the vision model whose output the checker reads, which can return
  anything; and a coding agent that writes this repository, which could edit a number, a label or
  a test by mistake or to make a check pass.

## A bored participant

| What they could do | What stops it | Test | Stopped? |
|---|---|---|---|
| Rebuild the key through judge mode before the lock | judge mode's answer route answers 403 until 2026-09-28T01:00:00Z, on both servers | `apps/api/tests/test_study.py::test_demo_answer_is_shut_before_the_lock`, `worker/test/e2e.mjs` ("judge mode shut before the lock" and "judge mode open at the lock", with the Worker's clock fixed one second before the lock and at it), `scripts/tests/test_worker_lock.py::test_the_worker_lock_is_the_python_lock` | yes |
| Read the key from the site's files or from an answer | no served file carries a gold label, or the build fails (`apps/web/scripts/check-bundle.mjs`); an answer's reply never says whether it was right | `apps/api/tests/test_study.py::test_response_body_never_reveals_correctness` | yes |
| Rebuild the key by taking the test again and again, reading the score per feature | only the first completed sitting from a browser counts in the analysis | `evals/tests/test_usability_analysis.py::test_repeat_token_keeps_only_the_first_completed_session` | no: a new browser is a new person, and the score screen shows each feature's score |
| Rebuild the key after the lock, when judge mode says right or wrong | nothing; the study is locked by then, and the route stores nothing | `apps/api/tests/test_study.py::test_demo_answer_stores_nothing` | no: a volunteer who does this can carry a perfect score into their creek checks |
| Fill the study with scripted sittings | a hidden form field marks simple bots; sittings under 40 seconds and repeats from a browser are left out by the tagged plan; one arm per browser | `apps/api/tests/test_study.py::test_hidden_field_marks_the_session_but_the_response_is_identical`, `evals/tests/test_usability_analysis.py::test_exclusions_follow_the_plan_order_and_count_each_rule`, `apps/api/tests/test_study.py::test_one_browser_keeps_one_arm_however_often_it_reloads` | partly: the Worker has no rate limit, on purpose, so a script that waits 40 seconds and clears its token is counted; the public counts would show the jump |
| Type something personal into the record | answers are choices from lists and free text is refused | `apps/api/tests/test_check.py::test_draft_refuses_free_text_and_unknown_items` | partly: a new spot's name is typed; the servers refuse long runs of digits and email addresses (`apps/api/check.py`), but a person's name typed as a spot name would be stored and shown |
| Upload a photo that gives away where they live | the Python API re-encodes every upload; the Worker cuts the metadata segments out; the phone's browser shrinks the photo before sending, which drops them too | `apps/api/tests/test_upload.py::test_upload_strips_exif_downsizes_and_serves_only_with_the_token`, `worker/test/e2e.mjs` ("quick check and upload"), `worker/test/golden.test.ts` ("uploads: ...", two tests) | yes: since Sep 24 the Worker's cut also drops everything after the end marker and metadata between scans, allows fill bytes, and refuses a JPEG it cannot walk, the shapes the Sep 23 review found (REVIEW_02 F01) |
| Read someone else's upload | a photo is served only with the one token handed to its uploader, and deleted after 30 days (on the Worker by the store's own expiry, `worker/src/uploads.ts`) | `apps/api/tests/test_upload.py::test_cleanup_deletes_uploads_older_than_thirty_days` | yes |

## A competitor

| What they could do | What stops it | Test | Stopped? |
|---|---|---|---|
| Change or delete our resources in the shared sandbox | nothing on their server: it is open to write. We can see it and put them back: every resource carries our tag, and the ledger lists every id we made | `scripts/tests/test_repush_sandbox.py::test_delete_refuses_unknown_ids_searches_and_operations` | no. Our own mirror deletes only ids in our ledger, never by search, so our mistakes cannot hit their data |
| Make us call OneAquaHealth's closed API | the mirror refuses that host by name | `scripts/tests/test_repush_sandbox.py::test_push_refuses_the_forbidden_host` | yes |
| Use up the database's daily read quota | Cloudflare's edge protection | none | no: the Worker has no rate limit, and `GET /api/skeleton` still writes a row and counts the table on every call (`SECURITY.md`, known gaps) |
| Say our numbers are made up | every number in the README and these docs is checked against `results/` in CI, and the raw answers and the cost of every call are committed | `scripts/tests/test_verify_claims.py::test_a_rendered_number_that_drifted_fails` | yes, as far as a file can prove it |
| Say we changed the key or the pass table after seeing the results | the key's hash was frozen and written to the audit log; the pass table's cells are graded again from its own runs; the analysis plan is tagged | `scripts/tests/test_committed_key.py::test_the_answer_key_is_the_one_that_was_frozen`, `evals/tests/test_committed_pass_table.py::test_every_passed_cell_follows_from_its_own_runs` | yes, as far as files can show it: the key was frozen on Sep 21, before any paid run, and every paid call is a line in `results/cost_log.jsonl`, so a run left out of `results/` would still show there |

## A curious judge

| What they could do | What stops it | Test | Stopped? |
|---|---|---|---|
| Open the anonymous export | without the token the route answers 404, as if it did not exist; the export holds no identifiers | `apps/api/tests/test_study.py::test_export_needs_the_token_and_returns_the_exact_schema`, `apps/api/tests/test_study.py::test_export_holds_no_identifier_columns` | yes |
| Guess the QA key to hide a sitting | secrets are compared in constant time and one shorter than 16 characters counts as not set; a wrong key is no error, the sitting is simply real | `apps/api/tests/test_study.py::test_qa_key_header_marks_a_test_session` | yes |
| Find a secret in the history | gitleaks over the history and a scan of every file git would commit, in `make check` | `scripts/tests/test_secret_scan.py::test_gitleaks_finds_nothing_new_in_this_history`, `scripts/tests/test_secret_scan.py::test_make_check_runs_gitleaks_and_the_tree_scan` | yes |
| Find a person's address in a log | the Python API writes no client address to any log line | `apps/api/tests/test_privacy.py::test_full_session_leaves_no_client_address_in_any_log_line` | yes for our code; Cloudflare keeps its own short edge records, which we do not read |
| Run the analysis on real data before the lock | the analysis reads the real clock and this repository, and no option or variable stands in for either | `evals/tests/test_usability_refusal.py::test_no_option_or_variable_fakes_the_clock_or_the_repo` | yes |
| Make the read only MCP server reach another route | it refuses any id that is not one plain name | `apps/mcp/tests/test_server.py::test_an_api_id_never_leaves_its_route` | yes |
| Load a script from somewhere else into the site | the site's Content Security Policy allows our own origin only | `apps/web/tests/landing.spec.ts` | yes |

## A model

| What it could do | What stops it | Test | Stopped? |
|---|---|---|---|
| Write the record | the record is built from human inputs only; no parameter can carry a flag, a model id or model text | `core/tests/test_gate.py::test_build_record_signature_carries_human_inputs_only`, `core/tests/test_gate.py::test_fuzz_model_output_never_reaches_answers_or_labels` | yes |
| Flag a feature it did not pass, or invent one | the gate keeps a flag only for a known feature that model passed | `core/tests/test_harden_gate_properties.py::test_every_kept_flag_is_licensed_for_that_exact_model` | yes |
| Send markup, control characters or text direction tricks to a person | the gate drops the note | `core/tests/test_harden_gate_properties.py::test_a_note_with_any_unicode_direction_control_is_dropped` | yes |
| Flood the gate or crash it | more than 50 candidates drops them all; the gate never raises | `core/tests/test_harden_gate_properties.py::test_a_flood_of_a_million_drops_everything`, `core/tests/test_harden_gate_properties.py::test_the_gate_never_raises_and_leaves_its_inputs_as_they_were` | yes |
| Follow instructions written in a photo | frames with readable text are screened out of the footage pool; the model's note can only ask the person to look again | `scripts/tests/test_make_frames.py::test_vision_drops_any_readable_text_because_it_can_give_the_answer_away` | partly: the gate checks a note's form, not its truth, so a wrong note in plain words reaches the person, labelled "the checker noticed" |
| As a coding agent: hand-edit a number in the README or a doc | `make verify-claims` compares every number with `results/` | `scripts/tests/test_verify_claims.py::test_a_rendered_number_that_drifted_fails` | yes |
| As a coding agent: turn a pass table cell to passed, or change a gold label | both are graded again from their own records in `make check` | `evals/tests/test_committed_pass_table.py::test_every_passed_cell_follows_from_its_own_runs`, `scripts/tests/test_committed_key.py::test_the_answer_key_is_the_one_that_was_frozen` | yes, unless it also rewrites the runs or the frozen hash, which a reviewer would see in the diff |
| As a coding agent: write a person's name as the approver of a sentence it wrote | nothing in code; a review on Sep 23 found one such sentence | none | no. A person has to read every approval |
| As a coding agent: weaken a test so it passes | a person reviews the diff, and a new guard is broken on purpose once to see it fail before it is trusted | none | no, not by code |

## What is not stopped, in one list

- The key can be rebuilt by retaking the test in fresh browsers, and after the lock through judge
  mode. A kept score is a measure of the person only if they did not do that.
- The Worker has no rate limit, so scripted sittings and a flood of requests are not stopped by
  our code.
- Anyone can change or delete our copies in the shared sandbox. The ledger lets us see it and
  push them again.
- A typed spot name can hold a person's name.
- Contributor tokens are stored in plain form. Anyone who reads the database, or the backups on
  the Mac, can use one. The backup folder is private to one account on that Mac.
- Model notes are checked for form, not truth.
- Approvals and tests written by a coding agent need a person to read them.
