# 0009. The paid model run may make direct calls instead of batches

- **Status:** accepted
- **Date:** 2026-09-23
- **Carried by:** commit 88d4a29 ("the answer tool's enum is three strings, and EVALS_SYNC=1 makes
  direct calls") and commit 19e5560 (the first real AI run); `evals/model_sweep.py`,
  `evals/footage.py`, `results/cost_log.jsonl`

## Context

The eval scripts sent every model call through the Batch API, which costs half as much. On the
night of the paid run, batches waited hours in the queue, and the first run had to be done again
because of the YAML enum bug (`WRITEUP.md`, part 7). A run that finishes days later cannot feed a
submission due within the week.

## Decision

`EVALS_SYNC=1` makes the same calls directly, one by one, at the full price. Everything else stays
the same: the prompts, the forced answer, the gate and the grading. The spending caps are counted at
the direct price when direct calls are on, and the footage run checks the spend so far before each
next model. The Batch API stays the default.

## Consequences

- A run finishes in the same sitting, at about twice the cost per call; a test pins that the
  estimate doubles (`evals/tests/test_model_sweep.py::test_a_direct_run_is_estimated_at_twice_the_batch_price`).
- Every call, batch or direct, is logged with its cost in `results/cost_log.jsonl`; a fake run logs
  to `results/cost_log_fake.jsonl` and spends nothing.
- The test double for the SDK refuses what the real SDK refuses, so a direct call cannot pass a
  test on a request the API would reject.
