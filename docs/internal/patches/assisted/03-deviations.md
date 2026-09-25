Summary: one line for docs/deviations.md, the offer of part 2 on part 1's score screen (UPDATE_31).

Where: append at the end of `docs/deviations.md`, as the newest dated line. Replace DATE with the
UTC date of the integration commit.

Text:

- DATE: part 1's score screen offers part 2 (UPDATE_31, `docs/analysis_plan_v2.md`). One card is added after the score and the lesson offer, with one line, "Eight more photos, two minutes, and this time a checker may ask you to look again.", a Start button that opens `/t2` and a No thanks button that records the decline. The test before the score, its photos, questions, order, scoring and the score screen itself do not change, and part 2's answers are stored in their own tables and never read by part 1's analysis. The panel's completion code stays where it was, after the score, so a person who declines has it too, and the same code is shown at the end of part 2. Why: the study measures whether the checker's question helps, and the only people who can take it without a new recruitment are those who just finished part 1. Before any part 2 session existed; `prereg-v2` was tagged first.
