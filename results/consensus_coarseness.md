# SYNTHETIC: can four photos per feature weight a group's votes?

Written by `evals/consensus_coarseness.py` from `results/consensus_coarseness.json` (seed 20260921). Made up people only, no real answers. Do not edit by hand: run `make consensus-coarseness`.

Each number is the mean share of voted items a random group gets right, in percent. The number in brackets is the difference from plain majority, in points. A star marks a method that clearly beats plain majority (by more than twice the Monte Carlo standard error).

## Summary

In groups of 5, plain majority is best in 3 of 5 skill patterns. Feature only weights clearly lose to plain majority in 5 of 5, by 12.1 to 20.6 points. A weighted method clearly beats plain majority in 1 of 5 (third_at_chance), by at most 1.1 points (shrunk_k6). Passers only clearly beats plain majority in 2 of 5 (uniform_per_person, third_at_chance), by at most 2.2 points.

## everyone at 0.70 (`equal`)

Skills: skill 0.70 for every person and feature. Share of people passing a half: 55.0 percent.

| method | groups of 3 | groups of 5 | groups of 7 |
|---|---|---|---|
| plain majority | 78.3 | 83.6 | 87.3 |
| feature only weights | 53.9 (-24.4) | 63.0 (-20.6) | 69.1 (-18.2) |
| feature weights shrunk to overall, k = 3 | 70.2 (-8.1) | 76.2 (-7.4) | 80.3 (-7.0) |
| feature weights shrunk to overall, k = 6 | 70.6 (-7.7) | 76.6 (-7.0) | 80.6 (-6.7) |
| overall weights | 69.1 (-9.2) | 75.6 (-8.0) | 79.9 (-7.4) |
| passers only (6 of 8) | 75.5 (-2.8) | 79.8 (-3.8) | 83.0 (-4.3) |

- Groups of 3, everyone at 0.70: plain majority is best (78.3 percent right). The best weighted method, feature weights shrunk to overall, k = 6, is 7.7 points behind plain majority; passers only is 2.8 points behind plain majority.
- Groups of 5, everyone at 0.70: plain majority is best (83.6 percent right). The best weighted method, feature weights shrunk to overall, k = 6, is 7.0 points behind plain majority; passers only is 3.8 points behind plain majority.
- Groups of 7, everyone at 0.70: plain majority is best (87.3 percent right). The best weighted method, feature weights shrunk to overall, k = 6, is 6.7 points behind plain majority; passers only is 4.3 points behind plain majority.

## normal around 0.70, sd 0.07, one skill per person (`normal_per_person`)

Skills: one draw per person from normal(0.70, sd 0.07), used for all four features. Share of people passing a half: 55.5 percent.

| method | groups of 3 | groups of 5 | groups of 7 |
|---|---|---|---|
| plain majority | 78.5 | 83.8 | 87.5 |
| feature only weights | 55.8 (-22.7) | 65.3 (-18.5) | 71.6 (-15.9) |
| feature weights shrunk to overall, k = 3 | 72.1 (-6.4) | 78.5 (-5.2) | 82.7 (-4.8) |
| feature weights shrunk to overall, k = 6 | 72.5 (-5.9) | 79.0 (-4.8) | 83.1 (-4.4) |
| overall weights | 71.2 (-7.2) | 78.2 (-5.6) | 82.7 (-4.9) |
| passers only (6 of 8) | 76.8 (-1.7) | 81.6 (-2.2) | 85.0 (-2.5) |

- Groups of 3, normal around 0.70, sd 0.07, one skill per person: plain majority is best (78.5 percent right). The best weighted method, feature weights shrunk to overall, k = 6, is 5.9 points behind plain majority; passers only is 1.7 points behind plain majority.
- Groups of 5, normal around 0.70, sd 0.07, one skill per person: plain majority is best (83.8 percent right). The best weighted method, feature weights shrunk to overall, k = 6, is 4.8 points behind plain majority; passers only is 2.2 points behind plain majority.
- Groups of 7, normal around 0.70, sd 0.07, one skill per person: plain majority is best (87.5 percent right). The best weighted method, feature weights shrunk to overall, k = 6, is 4.4 points behind plain majority; passers only is 2.5 points behind plain majority.

## uniform 0.50 to 0.95 per person and feature (`uniform_per_person_and_feature`)

Skills: one draw per person and feature from uniform(0.50, 0.95). Share of people passing a half: 61.6 percent.

| method | groups of 3 | groups of 5 | groups of 7 |
|---|---|---|---|
| plain majority | 81.6 | 86.9 | 90.5 |
| feature only weights | 64.1 (-17.5) | 74.5 (-12.5) | 80.9 (-9.6) |
| feature weights shrunk to overall, k = 3 | 77.2 (-4.3) | 84.0 (-2.9) | 88.1 (-2.4) |
| feature weights shrunk to overall, k = 6 | 77.3 (-4.3) | 83.8 (-3.1) | 87.9 (-2.6) |
| overall weights | 74.9 (-6.6) | 81.8 (-5.1) | 86.2 (-4.3) |
| passers only (6 of 8) | 80.0 (-1.6) | 84.9 (-2.0) | 88.4 (-2.1) |

- Groups of 3, uniform 0.50 to 0.95 per person and feature: plain majority is best (81.6 percent right). The best weighted method, feature weights shrunk to overall, k = 6, is 4.3 points behind plain majority; passers only is 1.6 points behind plain majority.
- Groups of 5, uniform 0.50 to 0.95 per person and feature: plain majority is best (86.9 percent right). The best weighted method, feature weights shrunk to overall, k = 3, is 2.9 points behind plain majority; passers only is 2.0 points behind plain majority.
- Groups of 7, uniform 0.50 to 0.95 per person and feature: plain majority is best (90.5 percent right). The best weighted method, feature weights shrunk to overall, k = 3, is 2.4 points behind plain majority; passers only is 2.1 points behind plain majority.

## uniform 0.50 to 0.95 per person, same for every feature (`uniform_per_person`)

Skills: one draw per person from uniform(0.50, 0.95), used for all features. Share of people passing a half: 60.2 percent.

| method | groups of 3 | groups of 5 | groups of 7 |
|---|---|---|---|
| plain majority | 81.5 | 86.8 | 90.4 |
| feature only weights | 64.1 (-17.3) | 74.5 (-12.3) | 81.0 (-9.4) |
| feature weights shrunk to overall, k = 3 | 79.1 (-2.4) | 86.2 (-0.7) | 90.3 (-0.1) |
| feature weights shrunk to overall, k = 6 | 79.6 (-1.8) | 86.7 (-0.2) | 90.7 (+0.3) * |
| overall weights | 78.8 (-2.7) | 86.4 (-0.5) | 90.6 (+0.2) * |
| passers only (6 of 8) | 82.0 (+0.5) * | 87.5 (+0.7) * | 91.1 (+0.7) * |

- Groups of 3, uniform 0.50 to 0.95 per person, same for every feature: passers only (6 of 8) is best, 0.5 points ahead of plain majority, a clear gain. The best weighted method, feature weights shrunk to overall, k = 6, is 1.8 points behind plain majority.
- Groups of 5, uniform 0.50 to 0.95 per person, same for every feature: passers only (6 of 8) is best, 0.7 points ahead of plain majority, a clear gain. The best weighted method, feature weights shrunk to overall, k = 6, is 0.2 points behind plain majority.
- Groups of 7, uniform 0.50 to 0.95 per person, same for every feature: passers only (6 of 8) is best, 0.7 points ahead of plain majority, a clear gain. The best weighted method, feature weights shrunk to overall, k = 6, is 0.3 points ahead of plain majority, a clear gain.

## 13 of 40 at 0.50, the rest normal around 0.80, sd 0.06 (`third_at_chance`)

Skills: exactly 13 of 40 people (40 / 3 rounded to the nearest whole person) at 0.50 on every feature; the rest one draw per person from normal(0.80, sd 0.06), used for all four features. Share of people passing a half: 57.5 percent.

| method | groups of 3 | groups of 5 | groups of 7 |
|---|---|---|---|
| plain majority | 78.8 | 84.2 | 88.0 |
| feature only weights | 61.7 (-17.1) | 72.1 (-12.1) | 78.7 (-9.2) |
| feature weights shrunk to overall, k = 3 | 77.4 (-1.4) | 84.7 (+0.4) * | 88.9 (+1.0) * |
| feature weights shrunk to overall, k = 6 | 78.1 (-0.7) | 85.3 (+1.1) * | 89.5 (+1.5) * |
| overall weights | 77.2 (-1.6) | 84.9 (+0.7) * | 89.3 (+1.4) * |
| passers only (6 of 8) | 80.5 (+1.7) * | 86.4 (+2.2) * | 90.2 (+2.2) * |

- Groups of 3, 13 of 40 at 0.50, the rest normal around 0.80, sd 0.06: passers only (6 of 8) is best, 1.7 points ahead of plain majority, a clear gain. The best weighted method, feature weights shrunk to overall, k = 6, is 0.7 points behind plain majority.
- Groups of 5, 13 of 40 at 0.50, the rest normal around 0.80, sd 0.06: passers only (6 of 8) is best, 2.2 points ahead of plain majority, a clear gain. The best weighted method, feature weights shrunk to overall, k = 6, is 1.1 points ahead of plain majority, a clear gain.
- Groups of 7, 13 of 40 at 0.50, the rest normal around 0.80, sd 0.06: passers only (6 of 8) is best, 2.2 points ahead of plain majority, a clear gain. The best weighted method, feature weights shrunk to overall, k = 6, is 1.5 points ahead of plain majority, a clear gain.

## Method

40 people, 4 features of 4 items. Yes or no only, so each vote is right or wrong; Can't tell is not modelled. Halves: for every feature 2 of its 4 items go to half A and 2 to half B; score on one half, vote on the other, then swap; results are over both ways. Groups of 3, 5, 7 drawn at random. 1000 populations per pattern, 8 random splits each used both ways, and 50 groups per size for each way, so 800,000 group votes per cell.

- plain majority: w = 1
- feature only weights: w = max(0, logit((c + 0.5) / 3))
- feature weights shrunk to overall, k = 3: r = (C + 0.5) / 9; p = (c + 0.5 + 3 * r) / (3 + 3); w = max(0, logit(p))
- feature weights shrunk to overall, k = 6: r = (C + 0.5) / 9; p = (c + 0.5 + 6 * r) / (3 + 6); w = max(0, logit(p))
- overall weights: w = max(0, logit((C + 0.5) / 9))
- passers only (6 of 8): people with C >= 6 vote by plain majority; when nobody in the group passed or the passers tie, the whole group votes by plain majority

c is right of the 2 calibration items of the voted item's feature; C is right of all 8 calibration items; logit(p) = ln(p / (1 - p)). A sum of exactly zero (a tie, including every weight zero) counts as wrong for every method; sums within the tie tolerance of zero are treated as zero to absorb floating point rounding.

Monte Carlo error: the largest standard error of a mean is 0.0017 and of a difference from plain majority 0.0012 (as shares, not percent).
