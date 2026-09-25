# Cost per assessment

Computed 2026-09-25T21:16:34Z by `uv run python scripts/harden_costs.py` from `results/cost_log.jsonl`. One line in the log is one model call, and one call judges one photo or one frame, so an assessment is one call. Only lines marked real count.

The log has 5065 lines and 5017 of them are real.

| Purpose | Model | Calls | Cost (USD) | Per assessment (USD) | Per 100 (USD) |
|---|---|---|---|---|---|
| benchmark | claude-fable-5-1 | 48 | 1.36791 | 0.028498 | 2.8498 |
| benchmark | claude-haiku-4-5-20251001 | 96 | 0.230745 | 0.002404 | 0.2404 |
| benchmark | claude-opus-5 | 48 | 0.636525 | 0.013261 | 1.3261 |
| benchmark | claude-opus-5-5 | 48 | 0.509304 | 0.010611 | 1.0611 |
| benchmark | claude-sonnet-5 | 96 | 0.453116 | 0.00472 | 0.472 |
| footage | claude-fable-5-1 | 600 | 13.93178 | 0.02322 | 2.322 |
| footage | claude-haiku-4-5-20251001 | 1200 | 2.601396 | 0.002168 | 0.2168 |
| footage | claude-opus-5 | 600 | 6.73884 | 0.011231 | 1.1231 |
| footage | claude-opus-5-5 | 600 | 5.780972 | 0.009635 | 0.9635 |
| footage | claude-sonnet-5 | 1200 | 5.137182 | 0.004281 | 0.4281 |
| model_sweep | claude-fable-5-1 | 48 | 1.35786 | 0.028289 | 2.8289 |
| model_sweep | claude-haiku-4-5-20251001 | 144 | 0.289623 | 0.002011 | 0.2011 |
| model_sweep | claude-opus-5 | 96 | 0.972452 | 0.01013 | 1.013 |
| model_sweep | claude-opus-5-5 | 48 | 0.517904 | 0.01079 | 1.079 |
| model_sweep | claude-sonnet-5 | 144 | 0.577946 | 0.004014 | 0.4014 |
| smoke | claude-haiku-4-5-20251001 | 1 | 0.002387 | 0.002387 | 0.2387 |

Per 100 is per 100 frames on the rows whose purpose is a footage run (benchmark_frames, footage, frames, video, walk), and per 100 photos on the others.
