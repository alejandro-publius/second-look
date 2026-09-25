# Patches for stage 2 (UPDATE_31)

Changes to files prompt 30 owns, written during stage 1 and applied at integration.

| File | One line |
|---|---|
| 01-end-screen-offer.patch | Part 1's score screen gains the Part2Offer card, and tests/part2-offer.spec.ts proves Start and No thanks (git apply). |
| 02-judges-door.patch | /judges renders JudgesAssistDoor, and the judges spec opens it (git apply). |
| 03-deviations.md | The deviation line for the offer on part 1's score screen. |
| 04-done-lines.md | The UPDATE_31 section of docs/internal/DONE.md, D120 to D138. |
| 05-panel-study.md | Panel study: about 8 minutes, reward raised, the optional block, the code at both ends. |
| 06-readme.md | README: the Evals paragraph, the Track 3 sentence, the second human row's place, the video line. |
| 07-lock-job.md | The lock job runs the part 2 analysis after part 1's and fills the second human row. |
| 08-stage2-steps.md | The integration order: merge, patches, tag, deploy, phone tests, report. |
