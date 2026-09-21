# SYNTHETIC results, not from people (real_gain scenario)

Stamp: SYNTHETIC. Generated 2026-09-21T00:05:52Z by evals/usability_analysis.py.

## Primary estimate (plan item 6)

| Quantity | Value |
|---|---|
| Status | confirmatory |
| Completed and kept, trained | 42 |
| Completed and kept, untrained | 42 |
| Mean accuracy, trained | 0.689 |
| Mean accuracy, untrained | 0.621 |
| Difference in points (trained minus untrained) | 6.8 |
| 95 percent bootstrap interval, points | 0.1 to 13.4 |
| Permutation p (two-sided) | 0.0510 |
| Hedges g | 0.435 |

## Sessions and exclusions (plan item 5)

| Count | Untrained | Trained |
|---|---|---|
| randomized | 51 | 52 |
| started | 50 | 49 |
| completed | 48 | 47 |
| analysed | 42 | 42 |

| Order | Rule | Removed | Remaining |
|---|---|---|---|
| 0 | started at or after the data lock (never analysed, plan item 7) | 3 | 103 |
| 1 | did not finish all 16 items | 8 | 95 |
| 2 | test finished in under 40 seconds | 3 | 92 |
| 3 | repeat visit from the same browser token (only the first completed session counts) | 4 | 88 |
| 4 | flagged as QA (is_test) | 2 | 86 |
| 5 | filled the hidden form field | 2 | 84 |
| 6 | dry run before launch | 0 | 84 |

## Per feature (plan item 4)

| Feature | Arm | Accuracy | Hit rate | False alarm rate | Can't tell |
|---|---|---|---|---|---|
| artificial_bank | untrained | 0.643 | 0.571 | 0.250 | 0.083 |
| artificial_bank | trained | 0.720 | 0.607 | 0.155 | 0.042 |
| dug_out_channel | untrained | 0.524 | 0.452 | 0.321 | 0.077 |
| dug_out_channel | trained | 0.643 | 0.595 | 0.202 | 0.113 |
| invasive_plant | untrained | 0.691 | 0.643 | 0.226 | 0.066 |
| invasive_plant | trained | 0.762 | 0.786 | 0.202 | 0.054 |
| pipe_running | untrained | 0.625 | 0.607 | 0.298 | 0.077 |
| pipe_running | trained | 0.631 | 0.631 | 0.345 | 0.036 |

## Other descriptives

- Share of Can't tell answers: untrained 0.076, trained 0.061.
- Share of Yes answers: untrained 0.421, trained 0.441.
- Median test time in seconds: untrained 106.3, trained 108.2.
- Median lesson time in seconds: trained 123.7 (n 42), untrained after the test 92.7 (n 23).
- Completed sessions by source: chat 16 untrained and 13 trained, creek_group 5 untrained and 5 trained, friends 10 untrained and 10 trained, other 3 untrained and 3 trained, poster 8 untrained and 11 trained.
- Warm-up item: w01 chosen by 0.333 (n 28), w02 chosen by 0.667 (n 56).

## Sensitivity checks (plan item 6)

| Check | n trained | n untrained | Difference, points | 95 percent interval | p |
|---|---|---|---|---|---|
| partial_completers_scored_wrong | 44 | 44 | 7.5 | -0.1 to 15.1 | 0.0665 |
| without_prior_experience | 31 | 32 | 7.6 | -0.2 to 15.6 | 0.0674 |

