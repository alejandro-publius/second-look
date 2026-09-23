# Second Look: update 11C (answers, approvals and the marks)

Pasted by Alex on 2026-09-21. Everything below is addressed to Claude Code.

Consent contact email: alejandro-publius@berkeley.edu

Answers to your three questions, and my approvals, so you can run without stopping. Save this as docs/updates/UPDATE_11C.md.

1. Yes, the pipe lesson needs photos with no pipe. Fetch these two through the same ingest, role lesson, feature pipe_running, label absent:
   - Karpacz Poland 088 a.jpg | https://commons.wikimedia.org/wiki/File:Karpacz_Poland_088_a.jpg | author Krzysztof Poplawski (keep the spelling from the source page) | CC BY-SA 4.0 | evidence: caption describes a natural rocky forest stream, no pipe or outfall in frame.
   - Le Train a Grez-Doiceau 005.jpg | https://commons.wikimedia.org/wiki/File:Le_Train_%C3%A0_Grez-Doiceau_005.jpg | author VerboseDreamer | CC BY-SA 3.0 | evidence: caption describes a natural meander with nettles on the banks, no pipe or outfall in frame.
   The two pipe contrast pairs become: the Lyme Brook outfall beside the Karpacz stream, and the Bierley outfalls beside Le Train. Move the EPA staining photo and the Wrea Brook outfall to the spare role. Check the scene rule again.
2. A research grade iNaturalist identification plus the species' page on the Cal-IPC inventory is enough to name a species on screen. Change the region pack rule to say that, with any team member able to verify. Use Cal-IPC's common names, for example Himalayan blackberry for Rubus armeniacus.
3. Keep the warm-up reveal on the end screen. You were right: before the test it would be a small lesson handed to both arms.

Wording, approved by Alex Velazquez today:
- Built banks: "Are the banks artificial, such as concrete or stones set in concrete?"
- Dug-out channel: "Has this channel been straightened or dug out?"
- Plants: the app's wording, "Do you see any non-native or invasive plant species?"
- Pipes: "Can you see a pipe or drain outlet that empties into this creek?"
- The four rules of thumb, the lesson captions and the practice feedback: approved as drafted, on three conditions you check by code or by reading: each rule is 12 words or fewer, each has a source you actually fetched, and none makes a health claim. Fix any that fail and say which.
- The consent text: approved with the email above.
Write the four questions into docs/analysis_plan.md. Print every approved string in the report, so the planner can read them before the tag.

Marks: do not wait for me to place them. Look at each lesson photo yourself and propose the marks: one or two per photo that shows the feature, each with a label of five words or fewer naming the cue, and none on a photo that does not show it unless a look-alike needs pointing out. Save them as approved false. Then start the review page, give me the local link, and wait for me to type: marks done. I will approve or drag them there.

After marks done: write "one labeller" into the plan and Known weaknesses unless a second label file exists, run freeze_key, check the two GitHub backup secrets (if they are missing, print the two commands and carry on), deploy main behind the is_test key, and print the link for the dry run with three friends. Do not tag prereg-v1. Then write the report, copy the full file to the clipboard with pbcopy, print the report block, and stop.
