# Cost per assessment

Computed 2026-09-22T18:27:32Z by `uv run python scripts/harden_costs.py` from `results/cost_log.jsonl`. One line in the log is one model call, and one call judges one photo or one frame, so an assessment is one call. Only lines marked real count.

The log has 48 lines and 0 of them are real.

No real lines, so there is no cost per assessment and no cost per 100 frames yet. No paid model run has been logged on this branch. The numbers arrive with the model run; run this script again after it.

The lines that are not real: 48 from benchmark. They cost 0 and say nothing about price. `evals/model_sweep.py` says fake runs write `results/cost_log_fake.jsonl`, so fake lines in the real log are worth a look.
