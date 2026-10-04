# The 20 hardest questions, with honest answers

For the live judging and for anyone reading the repo. First written in this repository's own pull request #5 (not the one we sent to hl7-eu/oah), checked against `main` on 2026-09-24; questions 4 and 18 were brought up to date on 2026-09-25, and questions 13, 15, 19 and 20 on 2026-09-30, for the second wave of the study. Short answers, then the file or command that proves each one. Where the honest answer is "not yet" or "no", it says so.

## Freshwater ecologist

**1. Can you judge a creek from one photo?**
Not fully, and we do not claim to. The test checks whether a person notices four features that are visible in a photo. For pipes, the label means a pipe or outlet is visible, not that it is running, because flow and pollution cannot be judged from a still. The dry weather rule is taught for the field.
Proof: `docs/analysis_plan.md` item 3; `content/features.yaml`.

**2. Four photos per feature is tiny. What does "4 of 4" really tell a city?**
It tells them this person noticed that feature four times out of four on known photos, on that date. It is coarse on purpose and we say so. That is also why we do not weight a group's votes by the score on a feature. Our simulation with made-up people, `results/consensus_coarseness.json`, found that weights from a feature's own photos did worse than a plain majority in every skill pattern we tried. Weights that also use a person's whole score, and leaving out low scorers, did a little better, but only when some people were close to guessing on every feature. What we will report after the lock is narrower: whether leaving out people who score near chance changes what a group gets right.
Proof: README, Known weaknesses, where the numbers are checked against the file; `results/consensus_coarseness.json` and its table `results/consensus_coarseness.md`, both marked SYNTHETIC, written by `evals/consensus_coarseness.py` (`make consensus-check` reruns it); `docs/analysis_plan.md` item 11. This page quotes no number from them because this page cites real results only. The older `results/consensus_synthetic.json` used an earlier weighting rule that is biased on a set this small, so it is not the proof and we do not quote it.

**3. Who set the right answers, and how do you know they are right?**
The key came from the picks file Alex Velazquez wrote with the planner, a Claude chat (commit 81e62ed), with each photo's own source as evidence. There is one labeller and no blind label yet, so read every accuracy figure as agreement with this key; the models graded against it are Claude models. That is listed as a weakness and as a deviation, not hidden.
Proof: `docs/DATA_CARD.md`; `docs/deviations.md`; `photos/manifest.csv` column `label_evidence`.

**4. "Invasive" depends on where you are. Whose list?**
A Bay Area list from the Cal-IPC Inventory, approved for the team by Alex Velazquez on 2026-09-25 after each species was checked against its Cal-IPC profile. The creek check's plant question, "Which ones?", offers the species on that list, Can't tell and None of these, and the list only where the spot is in the Bay Area; elsewhere, and on a video walk, it offers Can't tell and None of these and says the list is for the Bay Area. No free text is stored. The iNaturalist line shows research grade sightings of listed plants near a creek once a finished check there has answered the plant question; none has yet, so it shows nothing so far. The region file is swappable per city.
Proof: `content/regions/california-bay-area.yaml` (`approved: true`, `approved_by`, a Cal-IPC link per species); `content/form.yaml`, item `invasive_which`; `docs/adr/0011-inaturalist-context.md`.

## FHIR standards

**5. Does it really validate against the OneAquaHealth guide?**
The saved validation run checks sample records from both emitters against the guide pinned at hl7-eu/oah b907cf0, built from source with SUSHI 3.20.1. Golden vectors compare the Worker emitter with the Python reference on covered inputs. Observation and Location use the guide's profiles; the observer qualification and supporting resources also use base R4 conventions.
The saved run has zero errors, with warnings recorded in the result file and terminology checks enabled. It does not cover every input; the empty-target Provenance case is documented in docs/KNOWN_BUGS.md.
Proof: `fhir/ig.lock`; `results/fhir_validation.json`; `make fhir-validate`. <!-- claim: results/fhir_validation.json#/errors = 0 -->

**6. Why is a volunteer a Practitioner?**
Because `Observation.performer` has no better fit in R4 and the guide has no profile for a citizen observer. We know it is a stretch, and we asked the guide's authors which resource they want.
Proof: `docs/ig_proposal.md`, "What we are actually asking, first", item 2.

**7. Where does the score live, and does it expire?**
The score per feature is in the QuestionnaireResponse of the test sitting. The Practitioner carries a qualification for the test with a period of 90 days from the test date. Every Observation links to the Practitioner through `performer`, and through Provenance to the test sitting.
Proof: `core/records.py` (`SCORE_VALID_DAYS = 90`), used in `core/fhir_emit.py`; `fhir/golden/visit-strawberry-creek-1.json`.

**8. Did you write anything to their server you should not have?**
Only conditional creates, with our tag on every resource and every id in a ledger. We never delete by search and never expunge. The one exception is a conditional update on our own Library entry, matched by our own identifier.
Proof: `fhir/sandbox_ledger.jsonl`; CLAUDE.md hard rule 10.

## Agents and MCP

**9. Can the AI change what a volunteer answered?**
No. The record builder takes human answers only and refuses a flags argument. A property test throws random model output at it and checks the stored answers are always the human answers.
Proof: `core/tests/test_gate.py::test_fuzz_model_output_never_reaches_answers_or_labels`; `uv run pytest -q core/tests/test_gate.py`.

**10. When may a model speak at all?**
Only on a feature it passed: all four items right in at least two of three runs, on the same 16 photos people take. Then a flag can make one follow-up question eligible, and the person has already answered. The real run of Sep 23, Pacific time (Sep 24 UTC), four models: all four passed built banks; Claude Haiku 4.5, Claude Sonnet 5 and Claude Opus 5.5 passed dug-out channels; Claude Opus 5.5 and Claude Fable 5.1 passed pipes; no model passed invasive plants. A table that is not real licenses nothing.
Proof: `core/gate.py`; `results/model_pass_table.json` (`"real": true`); `core/tests/test_gate.py::test_synthetic_table_licenses_nothing`. <!-- claim: results/model_pass_table.json#/real = True -->

**11. What does the MCP server expose, and can an agent write?**
Read only, over our own records. Tools include listing creeks, a creek record, findings, an observer's score and "explain this number", and every answer carries the resource ids behind it.
Proof: `apps/mcp/server.py`; `examples/mcp/README.md`; `examples/mcp/transcript.md`.

**12. What text from a model does a person ever see?**
Only a short note labelled "the checker noticed". Health and ecology sentences come only from an approved list with sources.
Proof: `content/approved_sentences.yaml`; CLAUDE.md hard rule 5; `core/tests/test_gate.py::test_note_with_markup_or_a_direction_control_is_dropped`.

## Digital health and outreach

**13. Did the lesson actually help people?**
No human benefit was estimated from the first wave: its analysis included no eligible completed sittings and reported an empty arm. The second-wave lock under plan v3 has now passed. This checkout contains the plan, but no second-wave result or evidence that a paid panel launched. The plan permits a paid panel beside the public link and defines how to report a sufficiently large sample or a smaller descriptive result. The owner's scheduled-job status needs checking before claiming that the analysis ran. Earlier access to judge mode could expose the answer key; the plan records that limitation.
Proof: `docs/analysis_plan.md` item 7; `docs/analysis_plan_v3.md` items 1, 5 and 7; `results/usability_20260929.md`; `docs/deviations.md`.

**14. Is the health advice safe?**
Each sentence is approved with a source and a quote from that source. We never state a risk for a specific site and never diagnose.
Proof: `content/approved_sentences.yaml` (`source`, `source_quote`, `approved_by`).

**15. What do you keep about people?**
For the test: a random session id and a hashed random browser token, no names, emails, IPs or free text. Part 2, the second look, adds its own answers and times, joined to the test by the session id. For the creek check: a random contributor token, the language the questions were shown in, EXIF stripped, uploads private and deleted after 30 days.
Proof: `docs/DATA_HANDLING.md`; `apps/api/tests/test_privacy.py`.

**16. Is it readable for a 12 year old?**
The readability check measures the text it covers against a cap, with documented exceptions. That is a useful editing check, not evidence that every intended reader understands every screen.
Proof: `make readability`; `content/readability_exceptions.yaml`.

## Engineering

**17. How do we know the numbers in the README are real?**
Marked numerical claims point into `results/`, and `scripts/verify_claims.py` detects drift in those claims. This checks consistency with saved files, not the truth of every sentence or the validity of a scientific conclusion. `make reproduce` independently regrades the runs for which raw evidence was retained and names its exceptions.
Proof: `make verify-claims`.

**18. Can a judge check it without a key or the network?**
Yes, with one limit it names. `make judge-check` runs the tests, grades the AI numbers in `results/` again from the committed raw model replies wherever a run kept them (`make reproduce`), reads the last HL7 validator run against the pinned guide, the web build and design gate, the audit chain and a secret scan, with no key. The benchmark runs kept counts, not replies, so their right-answer counts, their share of can't tell answers and their count of malformed replies are checked only as recorded: `make reproduce` prints a note under each such file, and judge-check prints those notes in its summary. The footage runs' answers on the adversarial frames are as recorded too, and three old synthetic files are not graded again.
Proof: `make judge-check`; `Makefile`.

**19. Is CI green?**
Answer on the day from the Actions tab. As of Sep 30 the last run that started, at 93bb002 on Sep 26, was green on both branches. From a334b11 on, GitHub has started no job: each run ends in about 3 seconds with GitHub's own note that the account's payments failed or its spending limit needs to be raised. Those notes attribute the interruption to account billing; inspect the current Actions diagnostic before treating that as confirmed today. `make check` and `make judge-check` have different scopes, including fresh versus saved FHIR validation evidence. Before that it was red at times from Sep 21 to Sep 24 for reasons outside the product (a runner without the browser, tests that read a folder only the Mac had, a lockfile written by a newer npm than CI's). It was red on Sep 24 from 0326e78 to bef7015, and on Sep 25 at e9898ed and 635955f, when a test count moved and WRITEUP.md and docs/ACCEPTANCE.md were rendered but not committed; since then `make test-counts` renders every doc itself and `verify-claims` names the doc that drifted. On Sep 25 two browser tests also timed out or raced on depth (90c4045 and 65a4a29) and were made robust. It was green on both branches again from a7b563a to 93bb002.
Proof: https://github.com/alejandro-publius/second-look/actions

## Blockchain

**20. Is this on a blockchain?**
No. It is a hash-chained audit log: each line carries the hash of the one before, so a changed line breaks the chain. So far it records the key freeze, the launch wipe, the three plan tags (`prereg-v1`, `prereg-v2` and `prereg-v3`), the sandbox re-push of Sep 28 and the first data lock; this checkout does not yet contain the second wave's lock entry. No tokens, no consensus, no ledger shared with anyone. Since Sep 24 its last hash is stamped with OpenTimestamps on each day the log has changed, a public timestamp service that anchors many hashes in one Bitcoin transaction: a timestamp for our log, not a chain of ours (`/verify`, `proofs/`).
Proof: `audit/log.jsonl`; `uv run python scripts/verify_audit.py`; `docs/notes/plan_hash.md`.
