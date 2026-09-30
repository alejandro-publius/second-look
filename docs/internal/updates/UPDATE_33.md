# Second Look: prompt 33 (planner update, pasted on 2026-09-29; the deadline was extended)

Alex pasted this into the running session of prompt 32 on Tue Sep 29 and confirmed it in his own
words: all of it, and judge mode shut again until the second lock.

Planner update: the deadline was extended. First, read the new deadline from the Devpost page and update every date that depends on it: the status issue, docs/ALEX_TODO.md, docs/SUBMISSION_DAY.md and docs/internal/DONE.md. Freeze is 36 hours before the new deadline; make go-public runs the morning before the deadline day.

1. The lock job comes first and runs alone: pause the fix wave and the audit until it has pushed, deployed, and filled the README's human rows, with judge mode open. Retry through network drops.
2. Then let the fix wave finish at no more than two heavy jobs at a time, so make check does not take 20 minutes. Merge only reviewed packages that pass make check and touch nothing in /t, /t2, the study endpoints or the analysis plans. After each deploy, run the phone tests and the read-only live check, record last known good, and fast-forward ~/second-look-depth.
3. The audit: finish only the lenses already started, fix what they confirm above minor, and start no new audit, critic or simulation after that.
4. If no real participant took part before the first lock, prepare a second wave: plan v3, the same design and analysis as v1 and v2, with its own lock set 48 hours before the new deadline, tagged and anchored before any new session, reported as its own README row, and extend the lock job with a second scheduled run at that time. Update docs/internal/PANEL_STUDY.md for the launch, and put "launch the panel" at the top of my steps.
5. When all of that is merged: make submit-check, the top of the status issue rewritten with only my steps in order with dates, the report to the clipboard with pbcopy, the report block printed, and stop.

## What the Devpost page said on 2026-09-29 at 20:56 UTC

Read without logging in, from https://oneaquahealth-ieee-hackathon.devpost.com/ and its
/details/dates page.

| Period | Begins | Ends |
|---|---|---|
| Submissions | September 14 at 9:00 AM PDT | October 04 at 9:00 PM PDT |
| Judging | October 05 at 9:00 AM PDT | October 15 at 5:00 PM PDT |
| Winners announced | | October 24 at 9:00 AM PDT |

Their rules page still says "Hackathon Period: September 16 to September 30, 2026", "Judging:
October 1 to October 15" and "Projects must be original and developed during the hackathon
period". The two pages disagree, so Alex asks the organizers which holds (docs/ALEX_TODO.md).

## The dates that follow

| What | Pacific time | UTC |
|---|---|---|
| The deadline | Sun Oct 4, 21:00 PDT | 2026-10-05T04:00:00Z |
| The second lock, 48 hours before it | Fri Oct 2, 21:00 PDT | 2026-10-03T04:00:00Z |
| The lock job's second run, ten minutes after that lock | Fri Oct 2, 21:10 PDT | 2026-10-03T04:10:00Z |
| make go-public, the morning before the deadline day | Sat Oct 3, by 08:00 PDT | 2026-10-03T15:00:00Z |
| The freeze, 36 hours before the deadline | Sat Oct 3, 09:00 PDT | 2026-10-03T16:00:00Z |
| Submit on Devpost, with three hours to spare | Sun Oct 4, by 18:00 PDT | 2026-10-05T01:00:00Z |
