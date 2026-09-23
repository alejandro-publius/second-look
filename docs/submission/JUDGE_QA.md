# The 20 hardest questions, with honest answers

For the live judging and for anyone reading the repo. From pull request #5, checked against this branch on 2026-09-23. Short answers, then the file or command that proves each one. Where the honest answer is "not yet" or "no", it says so.

## Freshwater ecologist

**1. Can you judge a creek from one photo?**
Not fully, and we do not claim to. The test checks whether a person notices four features that are visible in a photo. For pipes, the label means a pipe or outlet is visible, not that it is running, because flow and pollution cannot be judged from a still. The dry weather rule is taught for the field.
Proof: `docs/analysis_plan.md` item 3; `content/features.yaml`.

**2. Four photos per feature is tiny. What does "4 of 4" really tell a city?**
It tells them this person noticed that feature four times out of four on known photos, on that date. It is coarse on purpose and we say so. That is also why we do not weight a group's votes by the score on a feature. Our simulation with made-up people, `results/consensus_coarseness.json`, found that weights from a feature's own photos did worse than a plain majority in every skill pattern we tried. Weights that also use a person's whole score, and leaving out low scorers, did a little better, but only when some people were close to guessing on every feature. What we will report after the lock is narrower: whether leaving out people who score near chance changes what a group gets right.
Proof: README, Known weaknesses, where the numbers are checked against the file; `results/consensus_coarseness.json` and its table `results/consensus_coarseness.md`, both marked SYNTHETIC, written by `evals/consensus_coarseness.py` (`make consensus-check` reruns it); `docs/analysis_plan.md` item 11. This page quotes no number from them because this page cites real results only. The older `results/consensus_synthetic.json` used an earlier weighting rule that is biased on a set this small, so it is not the proof and we do not quote it.

**3. Who set the right answers, and how do you know they are right?**
One labeller, Alex Velazquez, from written definitions and from what each photo's own source says about it. No second labeller was available, so there is no agreement figure. That is listed as a weakness, not hidden.
Proof: `docs/analysis_plan.md` item 3; `photos/manifest.csv` column `label_evidence`.

**4. "Invasive" depends on where you are. Whose list?**
The Bay Area list from the Cal-IPC Inventory. Every plant we call invasive is on it, and the region file is swappable per city.
Proof: `content/regions/california-bay-area.yaml`; `content/regions/heraklion.yaml` for a second region.

## FHIR standards

**5. Does it really validate against the OneAquaHealth guide?**
Yes. The guide is pinned at hl7-eu/oah b907cf0 and built from source with SUSHI 3.20.1, and CI runs the HL7 validator over every emitted resource.
<!-- claim: results/fhir_validation.json#/errors = 0 -->
The latest run has zero errors.
Proof: `fhir/ig.lock`; `results/fhir_validation.json`; `make fhir-validate`.

**6. Why is a volunteer a Practitioner?**
Because `Observation.performer` has no better fit in R4 and the guide has no profile for a citizen observer. We know it is a stretch, and we asked the guide's authors which resource they want.
Proof: `docs/ig_proposal.md`, "What we are actually asking, first", item 2.

**7. Where does the score live, and does it expire?**
On the Practitioner, as a qualification with a period of 90 days from the test date. Every Observation links to it through `performer` and through Provenance.
Proof: `core/records.py` (`SCORE_VALID_DAYS = 90`), used in `core/fhir_emit.py`; `fhir/golden/visit-strawberry-creek-1.json`.

**8. Did you write anything to their server you should not have?**
Only conditional creates, with our tag on every resource and every id in a ledger. We never delete by search and never expunge. The one exception is a conditional update on our own Library entry, matched by our own identifier.
Proof: `fhir/sandbox_ledger.jsonl`; CLAUDE.md hard rule 10.

## Agents and MCP

**9. Can the AI change what a volunteer answered?**
No. The record builder takes human answers only and refuses a flags argument. A property test throws random model output at it and checks the stored answers are always the human answers.
Proof: `core/tests/test_gate.py::test_fuzz_model_output_never_reaches_answers_or_labels`; `uv run pytest -q core/tests/test_gate.py`.

**10. When may a model speak at all?**
Only on a feature it passed: all four items right in at least two of three runs, on the same 16 photos people take. Then a flag can make one follow-up question eligible, and the person has already answered. The real model run has not happened yet; until it does, the pass table is synthetic and licenses nothing. `make ai-run` is the one command for it, once Alex confirms the model ids and prices.
Proof: `core/gate.py`; `results/model_pass_table.json` (`"real": false` today); `core/tests/test_gate.py::test_synthetic_table_licenses_nothing`.

**11. What does the MCP server expose, and can an agent write?**
Read only, over our own records. Tools include listing creeks, a creek record, findings, an observer's score and "explain this number", and every answer carries the resource ids behind it.
Proof: `apps/mcp/server.py`; `examples/mcp/README.md`; `examples/mcp/transcript.md`.

**12. What text from a model does a person ever see?**
Only a short note labelled "the checker noticed". Health and ecology sentences come only from an approved list with sources.
Proof: `content/approved_sentences.yaml`; CLAUDE.md hard rule 5; `core/tests/test_gate.py::test_note_with_markup_or_a_direction_control_is_dropped`.

## Digital health and outreach

**13. Did the lesson actually help people?**
We do not know yet and we will not pretend. Recruitment was dropped. Sessions that arrive through the public link are reported as a description with their count, and nothing depends on them.
Proof: `docs/analysis_plan.md` item 7; `docs/deviations.md`.

**14. Is the health advice safe?**
Each sentence is approved with a source and a quote from that source. We never state a risk for a specific site and never diagnose.
Proof: `content/approved_sentences.yaml` (`source`, `source_quote`, `approved_by`).

**15. What do you keep about people?**
For the test: a random session id and a hashed random browser token, no names, emails, IPs or free text. For the creek check: a random contributor token, EXIF stripped, uploads private and deleted after 30 days.
Proof: `docs/DATA_HANDLING.md`; `apps/api/tests/test_privacy.py`.

**16. Is it readable for a 12 year old?**
Every string a person can see is measured in CI and fails above the cap.
Proof: `make readability`; `content/readability_exceptions.yaml`.

## Engineering

**17. How do we know the numbers in the README are real?**
Each number carries a claim that points into `results/`, and `scripts/verify_claims.py` fails CI if one drifts. No number is typed by hand.
Proof: `make verify-claims`.

**18. Can a judge check it without a key or the network?**
Yes: `make judge-check` runs the tests, FHIR validation against the pinned guide, the web build and design gate, the audit chain and a secret scan, with no key.
Proof: `make judge-check`; `Makefile`.

**19. Is CI green?**
Answer on the day from the Actions tab. It was red on Sep 21 and 22 for reasons outside the product (a runner without the browser, tests that read a folder only the Mac had); pull requests #2 and #3 fixed both, and it has been green since.
Proof: https://github.com/alejandro-publius/second-look/actions

## Blockchain

**20. Is this on a blockchain?**
No. It is a hash-chained audit log: each line carries the hash of the one before, so a changed line breaks the chain. It records the plan tag, the key freeze, the wipe, the lock and record writes. No tokens, no consensus, no ledger shared with anyone.
Proof: `audit/log.jsonl`; `uv run python scripts/verify_audit.py`; `docs/notes/plan_hash.md`.
