# Second Look: update 11D (reveal wording, marks approved, backups, dry run)

Pasted by Alex on 2026-09-21. Everything below is addressed to Claude Code.

The planner has read the approved strings in your report and clears them, with one change. Save this as docs/updates/UPDATE_11D.md.

1. The warm-up reveal must not say "the one on the right": on a phone the photos stack, and the order may be shuffled. Show both photos again with the more natural one marked, and use: "The messier creek is in a more natural state. Tidy is not the same as natural." Keep the second sentence about testing as it is. Add a test that the reveal is right whichever order the photos were shown in.
2. Marks: I, Alex Velazquez, approve all 24 marks as proposed. Stamp them with my name and today's date, stop the marking server, and save one image per lesson photo with its marks drawn on it to docs/screens/marks/, so they can be checked at a glance later. Treat this message as "marks done".
3. One labeller: write it into docs/analysis_plan.md and into Known weaknesses. Then run freeze_key.
4. Backups without GitHub secrets: use the wrangler login already on this Mac. make backup runs wrangler d1 export into ~/second-look-backups/, outside the repo. Run it once now, do the restore drill once against a scratch database, and install a launchd job that runs it daily at 21:00 and at wake. Preflight accepts a backup newer than 26 hours. Leave the GitHub workflow on manual.
5. Deploy main behind the is_test key, run the phone end-to-end tests against the deployed URL, and print one dry-run link I can text to friends, with a line saying what to tell them.
6. Run make preflight-launch and print what is still red. Do not tag prereg-v1.
7. Write the report, copy the full file to the clipboard with pbcopy, print the report block, and stop.
