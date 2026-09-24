# Second Look: prompt 29 (undeniable)

Alex: paste this into the goal window. It queues behind whatever is running and does not interrupt it. Two items in it need you for about 20 minutes in total, and they are the two that matter most; they are marked HUMAN with the exact steps.

Everything below is addressed to Claude Code.

## Order: this comes last

When this message arrives, do not stop or reorder what you are doing. Append the sections below to the end of `docs/internal/PLAN_TO_DONE.md` as its last block, and add their lines to the end of `docs/internal/DONE.md`. The loop takes the top RED item in file order, so nothing here starts until every earlier item (from updates 23, 24, 25, 27, 28 and the planner's README fixes) is PASS, HUMAN or BLOCKED. If you are reading this in a fresh window with no loop running, read `CLAUDE.md`, `PLAN.md`, `docs/HANDOFF_NEXT.md`, `docs/internal/PLAN_TO_DONE.md` and `docs/internal/DONE.md` first, finish the earlier items, and only then take these. The one exception is section 1's HUMAN step: write `docs/internal/PANEL_STUDY.md` and the `?src=panel` end screen change as soon as this arrives, because Alex needs them by Sep 26 evening and the panel study needs hours to run before data lock.

## 0. Why

Everything so far makes the project strong. Two gaps still let a judge say "but": the README's human row is empty, and "Contributed back" is a proposal nobody has seen. This run closes both and adds the proofs that no other entry will have. Save this text as `docs/internal/updates/UPDATE_29.md`. Every section becomes RED lines in `docs/internal/DONE.md` with proving commands. Same rules as always, with one change: the two-minute test flow may change only where section 1 says, as a logged deviation. Paid calls are not capped.

## 1. Real strangers, paid, not recruited

The analysis plan was tagged before any participant. The test is live, anonymous and consented. What is missing is people. A paid research panel supplies them in hours without anyone recruiting: participants open the link, take the test, and enter a completion code.

1. Prepare the study, software side:
   - When the link carries `?src=panel`, the end screen shows a fixed completion code after the score, and nothing else changes. Store the source label only, never any panel identifier from the URL: strip every query parameter except `src` before anything is stored, with a test. Log this as a deviation in `docs/deviations.md`, because it touches the end screen.
   - Add one sentence to the consent screen for that source only: "You are taking part through a research panel and will be paid by the panel; nothing about you is stored here." Test that the sentence appears only for that source.
   - Write `docs/internal/PANEL_STUDY.md`: the study title, a plain description for participants, the estimated time (5 minutes), the payment at or above the panel's minimum hourly rate, the screening (adults, English), the device note (phone or laptop both work), the target of 80 completed sessions, the completion code, the exact link, and how to watch progress with the counts endpoint. Add a `make panel-status` that prints completed sessions by source and by arm.
   - Confirm the analysis script handles the source label and the lock exactly as the tagged plan says, on synthetic data.
2. HUMAN, Alex, 15 minutes, by Sep 26 evening: create an account on a research panel such as Prolific, fund it (about 300 dollars covers 80 participants at a fair rate plus fees), create the study from `docs/internal/PANEL_STUDY.md`, and launch it. Nothing else is needed from him; the study runs itself.
3. After data lock (2026-09-28T01:00:00Z): run the pre-registered analysis once, exactly as tagged, and put the result in the README's human row and the numbers table, whatever it shows. If the panel was not launched, the row stays as it is and says so.

## 2. Contribute back now, not on Sep 30

Their repository is public, so a fork and a pull request do not expose ours.

1. Fork `hl7-eu/oah` under Alex's account, add the citizen example and the proposal from `docs/ig_proposal.md` on a branch, make sure the guide builds with it, and open the pull request with a plain description: what the example is, what the validator said, the three gaps, and the question of which resource should stand for a citizen observer.
2. Open two issues on `hl7-eu/oah`: the `morophology` spelling in their temporary code system, and `SpecimenOah.collection.collector` allowing only a PractitionerRole. Friendly, short, with the file and line.
3. Post the sandbox DNS finding as an issue there too, with the authoritative NXDOMAIN evidence, since the guide links to the sandbox.
4. The README's "Contributed back" section links the pull request and the issues by number. HUMAN only if `gh` cannot fork or open them from this Mac; then print the exact commands.

## 3. Time that cannot be argued with

1. Anchor the pre-registration: timestamp the `prereg-v1` tag object and `docs/analysis_plan.md` with OpenTimestamps (`ots stamp`), commit the `.ots` proofs, and upgrade them when the calendar confirms. Anchor the audit chain head the same way once a day from the launchd job.
2. `/verify` shows, for a record, its receipt, its chain position, and the OpenTimestamps proof status with the block height once confirmed. Say plainly what OpenTimestamps is and that it is a public timestamp service, not our own chain.
3. Add both to the trust table with the commands that check them.

## 4. Every number, rebuilt from raw

1. The raw model responses from every paid run are committed as fixtures (no keys, no personal data), and `make reproduce` re-grades every number in `results/` from those fixtures and the synthetic seeds, with no network and no key, and fails if any committed number differs. Put the command in the README's Evals section and in `make judge-check`.
2. Mutation testing on `core/` with `mutmut` or equivalent: report the score in `results/` and the README's numbers table, and kill surviving mutants until the score is at or above 85 percent on the gate, the follow-up selector, scoring and the FHIR emitter.
3. Lighthouse on the landing page: performance, accessibility, best practices and SEO all at 95 or above on the throttled profile, recorded in `results/`.

## 5. The documents that serious projects have

1. `docs/MODEL_CARD.md` for the checker: what it may do, what it may not, the pass table, the benchmark and its size, known failure modes, cost, and the gate. Linked from the README's Track 3 statement.
2. `docs/THREAT_MODEL.md`: assets, who might attack (a bored participant, a competitor, a curious judge, a model), what each could do, and what stops it, with tests.
3. `docs/REPORT.pdf`, a technical report of about six pages built from the README and `results/` with pandoc: abstract, problem, method, the evidence tables, the FHIR mapping, limitations, and the contributions. Linked from the README and attached to the Devpost text.
4. `docs/DATA_CARD.md` for the photo and footage sets: sources, licences, labelling method, what is and is not labelled.

## 6. The second labeller, if Rachel has 15 minutes

Keep `scripts/label_photos.py` ready with the 16 test photos. If a second label file appears, merge it, report Cohen's kappa per feature, and update the plan's labelling section and the README's Known weaknesses. HUMAN, optional.

## 7. Then the loop

Rerun the adversarial review over everything new, the six-judge simulation with the change recorded, the critic against Tideline and Blackbox until two clean rounds, `make judge-check`, `make submit-check`, the full done list, and the status issue with only the human items and their dates.

## 8. iNaturalist, in case prompt 28 has not run

On the creek record page and on `/city`, one context line per creek listing research-grade iNaturalist observations of species on the region pack's invasive list within 300 metres of the creek's Locations in the last three years: species name, count, most recent date, and a link to the observations. Read the public iNaturalist API with a named user agent, at most one request a second, cached in D1 by a daily job on the Mac, with the fetch time shown. Never in the guided check, never before the invasive plant question is answered, never counted in any number, never used to decide anything. Attribute iNaturalist and its terms in `docs/THIRD_PARTY.md`, on the credits page and in the README's OneAquaHealth surfaces table, add an ADR, and degrade to "no recent sightings on record" when the API is down. Also credit iNaturalist in the lesson: the invasive plant photos in the lesson and the test are research-grade iNaturalist observations from California, by author and licence. If prompt 28 already did this, verify its line in `DONE.md` passes and move on.
