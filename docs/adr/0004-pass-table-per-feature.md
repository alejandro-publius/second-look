# 0004. A model may flag a feature only if it passed the people's test for it

- **Status:** accepted
- **Date:** 2026-09-20
- **Carried by:** commit e0b2fdc (models take the same test); `evals/model_sweep.py`,
  `results/model_pass_table.json`, `core/checker.py`, `core/tests/test_checker.py`

## Context

A model is good at some features and bad at others. We already measure people per feature with a
test of four photos each, so the fair question for a model is the same one. A synthetic pass table,
made by the fake client while no key existed, must never license a real flag.

## Decision

Each model takes the same 16-photo test as the volunteers, with the same frozen question wording,
three times. It passes a feature only when all four of that feature's photos are right in at least
two of the three runs (`docs/analysis_plan.md` item 8). The result is committed as
`results/model_pass_table.json`, per model and per feature. The gate and the checker read it, and
both refuse a table that does not say `"real": true`. The checker does not ask a model about a
feature it did not pass.

## Consequences

- A pass is a licence to ask one question, not a claim that the model is accurate. Four photos per
  feature is coarse, and the README says so.
- A new model says nothing until it has taken the test: the models added in commit 8cecc38 speak
  only after a paid run writes their rows.
- The pass table changes only through a run of `evals/model_sweep.py`, never by hand, and every
  earlier run stays in `results/`.
