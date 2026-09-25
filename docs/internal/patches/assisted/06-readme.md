Summary: README for part 2: one paragraph under Evals with its tag, one sentence on the Track 3 line, and the place for the second human row.

Where: `README.md`, three edits. Every number stays a claim token or comes from the lock job;
nothing here is a hand-written number.

1. Line 1, the Track 3 statement: add one sentence at its end, before the model card sentence if
   that still reads well:

   `The AI's help is measured, not assumed: a second, pre-registered block tests whether the checker's one question makes people more accurate.`

2. Under `## Evals`, after the bullet on `evals/usability_analysis.py`, add:

   - Part 2, the assisted second look: after the score, people may take eight more photos. Half of them, at random in blocks of 4 within each part 1 group, meet the checker's one question, "The checker noticed something here. Look again?", whenever a flag the gate kept disagrees with their answer; they keep or change it, and their final answer is scored. The flags were computed once from the models' stored answers and the pass table ([`evals/assist_flags.py`](evals/assist_flags.py), [`results/assist_flags.json`](results/assist_flags.json)), so every person meets the same checker and no model is called while they answer. The plan was tagged `prereg-v2` before any part 2 session ([`docs/analysis_plan_v2.md`](docs/analysis_plan_v2.md), its hash in [`docs/notes/plan_hash.md`](docs/notes/plan_hash.md)). [`evals/assist_analysis.py`](evals/assist_analysis.py) was tested on three synthetic cases, the question helps, does nothing, or leads people to wrong answers, and runs once after the lock.

3. In `## Numbers at a glance`, right after the human row block (`<!-- /human-row -->`), add the
   place the lock job fills:

   ```
   <!-- human-row-2 -->
   Does the checker's question help? Part 2 is analysed once, after the data lock, as tagged in `prereg-v2`.
   <!-- /human-row-2 -->
   ```

4. The video's voice script (`docs/video_script.md`): add one line only if a beat that shows the
   gate or the checker's question has room without cutting anything: `And we test whether its
   one question helps: half the people who take the second look get it, half do not.` If no
   beat has room, leave the script and say so in the report.
