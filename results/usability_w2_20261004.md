# Usability test results (second wave)

Stamp: w2_20261004. Generated 2026-10-04T07:21:35Z by evals/wave2_analysis.py.

## Primary estimate (plan item 6)

| Quantity | Value |
|---|---|
| Status | not computed: an arm is empty |
| Completed and kept, trained | 0 |
| Completed and kept, untrained | 0 |
| Mean accuracy, trained | n/a |
| Mean accuracy, untrained | n/a |
| Difference in points (trained minus untrained) | n/a |
| 95 percent bootstrap interval, points | n/a |
| Permutation p (two-sided) | n/a |
| Hedges g | n/a |

## Sessions and exclusions (plan item 5)

| Count | Untrained | Trained |
|---|---|---|
| randomized | 33 | 33 |
| started | 31 | 32 |
| completed | 31 | 31 |
| analysed | 0 | 0 |

| Order | Rule | Removed | Remaining |
|---|---|---|---|
| 0 | started at or after the data lock (never analysed, plan item 7) | 0 | 66 |
| 1 | did not finish all 16 items | 4 | 62 |
| 2 | test finished in under 40 seconds | 61 | 1 |
| 3 | repeat visit from the same browser token (only the first completed session counts) | 0 | 1 |
| 4 | flagged as QA (is_test) | 0 | 1 |
| 5 | filled the hidden form field | 1 | 0 |
| 6 | dry run before launch | 0 | 0 |

## Per feature (plan item 4)

| Feature | Arm | Accuracy | Hit rate | False alarm rate | Can't tell |
|---|---|---|---|---|---|

## Other descriptives

- Share of Can't tell answers: untrained n/a, trained n/a.
- Share of Yes answers: untrained n/a, trained n/a.
- Median test time in seconds: untrained n/a, trained n/a.
- Median lesson time in seconds: trained n/a (n 0), untrained after the test n/a (n 0).
- Completed sessions by source: .
- Warm-up item: .

## Sensitivity checks (plan item 6)

| Check | n trained | n untrained | Difference, points | 95 percent interval | p |
|---|---|---|---|---|---|
| partial_completers_scored_wrong | 0 | 0 | n/a | n/a | n/a |
| without_prior_experience | 0 | 0 | n/a | n/a | n/a |


## The second wave

Plan: `docs/analysis_plan_v3.md`, tag `prereg-v3`. The design and the analysis are those of `prereg-v1` and `prereg-v2`.

A sitting counts when it started at or after 2026-09-30T04:00:00Z and before 2026-10-03T04:00:00Z. The stored post_lock mark is ignored.

- sittings_in_the_export: 66
- by_start_time, before_the_first_lock: 50
- by_start_time, between_the_first_lock_and_the_opening: 6
- by_start_time, inside_the_window: 10
- by_start_time, at_or_after_the_second_lock: 0
- by_start_time, no_start_time: 0
- stored_post_lock_marks_ignored: 16
