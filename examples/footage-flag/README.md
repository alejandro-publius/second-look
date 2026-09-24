# The checker on real creek footage: one flag kept, one dropped

On the live site the checker is off today (CHECKER_ENABLED), so no volunteer has seen a checker question. This is the paid footage run's record, not something a volunteer saw.

This page and [`example.json`](example.json) are written by [`evals/footage_example.py`](../../evals/footage_example.py) from committed files only. No model was called to make them. `make check` fails if either is not what the script writes.

## Where it comes from

- The run: [`results/footage_20260924T060539Z.json`](../../results/footage_20260924T060539Z.json), made at 2026-09-24T06:05:39+00:00. Its answers are in [`evals/fixtures/raw/footage_20260924T060539Z.jsonl`](../../evals/fixtures/raw/footage_20260924T060539Z.jsonl).
- The pass table its gate read: [`results/model_pass_table.json`](../../results/model_pass_table.json), made at 2026-09-24T05:47:56+00:00, before the run.
- In that run, 64 answers were yes, so 64 candidate flags went through the gate: 35 kept and 29 dropped. These are the gate numbers in [`results/footage_latest.json`](../../results/footage_latest.json); the script stops if they differ.
- The 35 kept flags by feature: `artificial_bank` 3, `dug_out_channel` 32, `invasive_plant` 0, `pipe_running` 0. The creek check has an item in [`content/form.yaml`](../../content/form.yaml) for `artificial_bank`, `invasive_plant` and `pipe_running`, and none for `dug_out_channel`. So a kept flag on `dug_out_channel` makes no question eligible: `select_followups` in [`core/followups.py`](../../core/followups.py) asks only about a feature the check has an item for.
- How the two frames were picked, by a fixed rule. Every yes answer in the run is a candidate flag. Only the candidates on a feature the creek check asks about, one with an item in content/form.yaml, are picked from. They are put in order by frame id, then model id, feature and run. The kept case is the first of them the gate kept, and the dropped case is the first of them the gate dropped.

## Kept: frame `v06-00403`

![Frame v06-00403, a still from a creek video filmed in United States](../../photos/benchmark/v06-00403.jpg)

Frame `v06-00403` from https://www.youtube.com/watch?v=CsayzeejVzY, by OkState Ag, licence CC-BY-3.0. File [`photos/benchmark/v06-00403.jpg`](../../photos/benchmark/v06-00403.jpg), with its row in [`photos/manifest.csv`](../../photos/manifest.csv).

1. **What the model was asked.** `claude-haiku-4-5-20251001` was asked the frozen question for `artificial_bank` from [`content/features.yaml`](../../content/features.yaml): "Are the banks artificial, such as concrete or stones set in concrete?" This is its answer from run 0 (the runs are numbered from 0).
2. **What the model answered.** Line 126 of [`evals/fixtures/raw/footage_20260924T060539Z.jsonl`](../../evals/fixtures/raw/footage_20260924T060539Z.jsonl), exactly as committed:

   ```json
   {"answer": "yes", "feature": "artificial_bank", "frame": "v06-00403", "malformed": false, "model": "claude-haiku-4-5-20251001", "note": "The stream bed shows carefully arranged stones/rocks that appear to be deliberately placed and set, characteristic of artificial bank construction rather than n", "run": 0}
   ```

   The fixture's first line says what it holds: "every answer as the run kept it (after forcing), and every call with its pass". So this is the answer after `force_answer` in [`core/checker.py`](../../core/checker.py) made it yes, no or can't tell with a short note, not the reply exactly as the model sent it.
3. **What the gate did.** The answer yes became the candidate flag `{"feature": "artificial_bank", "confidence": 1.0, "note": "The stream bed shows carefully arranged stones/rocks that appear to be deliberately placed and set, characteristic of artificial bank construction rather than n"}` (`candidate_flag` in [`evals/footage.py`](../../evals/footage.py)), and `parse_flags` in [`core/gate.py`](../../core/gate.py) read it with the model's name and [`results/model_pass_table.json`](../../results/model_pass_table.json).

   It kept it, as this Flag: `{"feature": "artificial_bank", "confidence": 1.0, "note": "The stream bed shows carefully arranged stones/rocks that appear to be deliberately placed and set, characteristic of artificial bank construction rather than n", "region": null}`. The pass table says `claude-haiku-4-5-20251001` passed `artificial_bank`: it got all 4 photos of that feature right in 3 of 3 runs. The rule is: all 4 items of a feature right in at least 2 of 3 runs (docs/analysis_plan.md item 8). The note is 160 characters long, the most `force_answer` keeps, so it is cut off there.
4. **What a person would then be asked.** `select_followups` in [`core/followups.py`](../../core/followups.py), called the way [`apps/api/check.py`](../../apps/api/check.py) calls it, with no answers, no test score, rain unknown, the rules in [`content/followups.yaml`](../../content/followups.yaml) and the checker switched on, and this one flag, makes one question eligible: `checker_flag`. It is a pure function: it reads no file, calls no model and uses no network.

   > **The checker noticed something that may be concrete walls and other built banks. Want to look again?**
   >
   > the checker noticed: The stream bed shows carefully arranged stones/rocks that appear to be deliberately placed and set, characteristic of artificial bank construction rather than n
   >
   > [I looked again] [Skip]

   Those are the words the walk page shows for a checker question ([`apps/web/components/WalkFlow.tsx`](../../apps/web/components/WalkFlow.tsx)): the question with the feature's plain words, then the model's note, and only there, after "the checker noticed". With the checker off, as on the live site today, the same call asks nothing.

   The person taps "I looked again" or "Skip", and no stored answer changes: the question asks them to look again, and the answers they gave before it stay as they were.
5. **What every model answered on this frame and feature.** From the same file.

   | Model | Passed this feature on the 16-photo test | Its answers, run by run |
   |---|---|---|
   | `claude-haiku-4-5-20251001` | yes | yes, yes, yes |
   | `claude-sonnet-5` | yes | cant_tell, cant_tell, cant_tell |
   | `claude-opus-5-5` | yes | cant_tell, cant_tell, cant_tell |
   | `claude-fable-5-1` | yes | cant_tell, cant_tell, cant_tell |

   Only a yes becomes a candidate flag. A no or a can't tell proposes nothing.

   The frame has no label in the manifest, so nobody has said whether the model was right. The flag decides nothing either way: it only lets the checker ask the person to look again, and what is kept is the person's answer.

## Dropped: frame `v02-00143`

![Frame v02-00143, a still from a creek video filmed in Russia](../../photos/benchmark/v02-00143.jpg)

Frame `v02-00143` from https://www.youtube.com/watch?v=vN5ArGGmdUY, by Красота Приморского края и не только, licence CC-BY-3.0. File [`photos/benchmark/v02-00143.jpg`](../../photos/benchmark/v02-00143.jpg), with its row in [`photos/manifest.csv`](../../photos/manifest.csv).

1. **What the model was asked.** `claude-haiku-4-5-20251001` was asked the frozen question for `pipe_running` from [`content/features.yaml`](../../content/features.yaml): "Can you see a pipe or drain outlet that empties into this creek?" This is its answer from run 0 (the runs are numbered from 0).
2. **What the model answered.** Line 61 of [`evals/fixtures/raw/footage_20260924T060539Z.jsonl`](../../evals/fixtures/raw/footage_20260924T060539Z.jsonl), exactly as committed:

   ```json
   {"answer": "yes", "feature": "pipe_running", "frame": "v02-00143", "malformed": false, "model": "claude-haiku-4-5-20251001", "note": "A dark pipe or drain outlet is visible on the right side of the stream, appearing to empty into the water.", "run": 0}
   ```

   The fixture's first line says what it holds: "every answer as the run kept it (after forcing), and every call with its pass". So this is the answer after `force_answer` in [`core/checker.py`](../../core/checker.py) made it yes, no or can't tell with a short note, not the reply exactly as the model sent it.
3. **What the gate did.** The answer yes became the candidate flag `{"feature": "pipe_running", "confidence": 1.0, "note": "A dark pipe or drain outlet is visible on the right side of the stream, appearing to empty into the water."}` (`candidate_flag` in [`evals/footage.py`](../../evals/footage.py)), and `parse_flags` in [`core/gate.py`](../../core/gate.py) read it with the model's name and [`results/model_pass_table.json`](../../results/model_pass_table.json).

   It dropped it. The gate's reason, in its own words: "flag 1: feature pipe_running not passed by model claude-haiku-4-5-20251001". The pass table says `claude-haiku-4-5-20251001` did not pass `pipe_running`: it got all 4 photos of that feature right in 0 of 3 runs. The rule is: all 4 items of a feature right in at least 2 of 3 runs (docs/analysis_plan.md item 8).
4. **What a person would then be asked.** Nothing from the checker. The gate kept no flag, so `select_followups` in [`core/followups.py`](../../core/followups.py), called the way [`apps/api/check.py`](../../apps/api/check.py) calls it, with no answers, no test score, rain unknown, the rules in [`content/followups.yaml`](../../content/followups.yaml) and the checker switched on, and no flag, makes no question eligible.
5. **What every model answered on this frame and feature.** From the same file.

   | Model | Passed this feature on the 16-photo test | Its answers, run by run |
   |---|---|---|
   | `claude-haiku-4-5-20251001` | no | yes, yes, yes |
   | `claude-sonnet-5` | no | no, no, no |
   | `claude-opus-5-5` | yes | no, no, no |
   | `claude-fable-5-1` | yes | no, no, no |

   Only a yes becomes a candidate flag. A no or a can't tell proposes nothing.

   The frame has no label in the manifest, so nobody has said whether the model was right. The gate does not judge that: it dropped the flag because this model did not pass this feature on the test, whatever the frame shows.
