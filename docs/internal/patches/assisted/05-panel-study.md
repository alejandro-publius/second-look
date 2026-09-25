Summary: docs/internal/PANEL_STUDY.md for part 2: about 8 minutes, the reward raised to match, the optional second block, the same code at both ends.

Where: `docs/internal/PANEL_STUDY.md`. Edit the rows and paragraphs named below in place; keep
anything prompt 30 added. Check the numbers against the file as it is then: the reward keeps the
same hourly rate as the 5 minute version.

1. Row "Description for participants", replace the text with:

   You will see photos of creeks and say, for each one, whether you can see one thing: a built bank, a dug-out channel, a plant that does not belong, or a pipe. Some people get a short lesson first. After your score you are offered an optional second block of eight more photos, where a checker may ask you to look again. It takes about 8 minutes with the second block, needs no camera, and works on a phone or a laptop. The completion code to paste back here is shown after your score if you skip the second block, and at the end of the second block if you take it. The test is anonymous: we store your answers and timings, never your name, your panel id or your address.

2. Row "Estimated time": `about 8 minutes (about 5 without the optional second look)`.

3. Row "Reward": `2.40 dollars (about 18 dollars an hour at about 8 minutes, the same rate as before), which is above the minimum hourly rate the panel shows when you set a reward. If the panel's minimum is higher on the day, use the minimum.`

4. Step 1, the funds: `about 450 dollars covers 80 people at the reward below plus the panel's fee, with room to spare.`

5. Row "Completion code": `SLCREEK26, the same code in two places: after the score, for everyone, and again at the end of part 2, the second look, for those who take it. Only for this link.`

6. Under "What a participant sees", add a paragraph:

   After the score, one line offers part 2, the second look: "Eight more photos, two minutes, and this time a checker may ask you to look again." It is optional. Half of those who start it, at random, meet the checker's question when the checker disagrees with their answer; the other half answer the same eight photos with no question (`docs/analysis_plan_v2.md`, tag `prereg-v2`). The completion code is on the score screen already, so a person who skips part 2 has it, and it is shown again at the end of part 2.

7. Under "Watching it", add: `make panel-status also prints part 2 by arm: started, finished and declined, from https://second-look-79t.pages.dev/api/t2/counts.`

8. Under "After the data lock", add: `The same job then runs the part 2 analysis once, as tagged in prereg-v2, and the README's second human row reports it, or says that too few finished part 2.`
