# Alex: what only you can do, in order

Working notes: the team's own to-do list, kept public on purpose. What is true of the product is
in the README.

Everything on this page needs your voice, your eyes or your account. Everything else is done.
Times are Pacific.

The deadline moved: Devpost now says submissions close on Sun Oct 4 at 21:00 PDT, and judging
runs from Oct 5 to Oct 15 (read on Sep 29, the team's working notes (UPDATE 33)). Nobody took the
test before the first lock on Sep 27, so a second wave of the study runs until Fri Oct 2 at
21:00 PDT under its own plan, and step 1 is what fills it.

Done for you on Sep 23 and 24: the two machine sittings of Sep 21 and 22 are marked as tests (on
Sep 25 our own judge walk finished one more sitting with the hidden field filled, which the plan's
exclusions leave out; `docs/deviations.md`), the model ids and prices were confirmed and the paid AI run, four models from Sep 24, is
in the README (its cost is logged in `results/cost_log.jsonl`), and the QA key is set on the Worker with a copy as `QA_KEY` in
`~/second-look/.env` and `~/second-look-depth/.env`. Copy that key and your API key to your
password manager when you can. Nobody films at a creek: the creek shots are open footage from
Wikimedia Commons, already in the rough cut and credited in `docs/video/CREDITS.md`. Contributed
back: hl7-eu/oah pull request 5 and issues 6, 7 and 8 are open under your account. Two daily jobs
on this Mac are new: the OpenTimestamps anchor (06:00) and the iNaturalist cache (07:45).

1. **From Tue Sep 29, 21:00, as early as you can, 15 minutes: launch the panel.** Wait until the
   top of the status issue says the second wave is open (judge mode shut again, plan v3 tagged
   and stamped). Then make a researcher account on Prolific, add about 450 dollars, create the
   study from the team's working notes (PANEL STUDY) (every field is written out there, the link and the
   completion code too) and publish it. The panel asks about ethics approval: its step 3 says
   what to check first. It runs by itself and must stop taking people a few hours before the
   second lock, Fri Oct 2 at 21:00; `make panel-status` shows how many have finished.

2. **Today, Tue Sep 29, 5 minutes: GitHub billing.** GitHub Actions has started no job since
   Sep 26: the account's payment failed or its spending limit is reached. On GitHub: Settings,
   Billing and plans. Until it is fixed no push is checked, and the README's check badge will
   show red on the public repository.

3. **By Wed Sep 30, 10 minutes: write to the organizers, two things in one message.** First,
   their dates page says submissions run to Oct 4, while their rules page still says "Hackathon
   Period: September 16 to September 30" and that projects must be developed in that period:
   ask which holds, so that work after Sep 30 is within the rules. Second, post
   the team's working notes (MESSAGE TRANSLATIONS): some of their app's translations seem to ask a
   different question from the English.

4. **Through Thu Oct 15: keep the Mac plugged in and awake.** On macOS 15: System Settings,
   Battery, Options, then turn on "Prevent automatic sleeping on power adapter when the display
   is off". Keep the lid open and the charger in: on Tue Sep 29 the battery fell to 4 percent
   in the middle of the work. The second lock's job runs on Fri Oct 2 at 21:10, and the uptime
   check and the daily jobs run only while the Mac is awake. On Fri Oct 2 from 21:00 to 22:00,
   run nothing heavy on the Mac (no `make check`, `make e2e` or `make dev` in any checkout).
   The job puts a notice on the Mac's screen when it is done or when it failed; at 21:50 look
   for "Second data lock done" on the status issue, and if it is not there, run
   `make lock-analysis-2` in `~/second-look-depth` that night and wait for it (about 30 minutes).
   Before 21:00 that day: if `~/second-look-backups/logs/repush.log` says their sandbox answered
   this week, commit `fhir/sandbox_ledger.jsonl` on depth by hand, so the audit line the job
   carries has its ledger row beside it.

5. **By Thu Oct 1, 20 minutes: Devpost.** Paste the fields from `docs/devpost.md` into the draft
   and invite Rachel to it. Upload the five gallery images in `docs/submission/gallery/` with
   their captions, and attach `docs/REPORT.pdf` where Devpost takes a file. For the live
   judging, read `docs/submission/JUDGE_QA.md`: the 20 hardest questions with honest answers.

6. **Optional, by Thu Oct 1, 20 minutes: record your voice.** Read
   `docs/video/teleprompter.html` in a browser (space pauses, the arrows change speed) and save
   the recording as `~/second-look-media/voice/voice.m4a` (or .wav or .mp3). Then
   `make video-final` lays it over the finished cut, keeps the captions as subtitles and writes
   `~/second-look-media/final/second-look-final.mp4` (`docs/video/README.md`). With no voice by
   the end of Thu Oct 1, the captions-only cut is the video.

7. **Thu Oct 1: the dry-run submission.** Fill every Devpost field except the video from
   `docs/devpost.md`, attach `docs/REPORT.pdf`, save the draft, and read it on your phone as a
   judge would. Then `make go-public GO=dry`, which changes nothing. The times and what to check
   after each step are in `docs/SUBMISSION_DAY.md`.

8. **By Fri Oct 2, 10 minutes: upload the video.** Upload
   `~/second-look-media/final/second-look-final.mp4` to YouTube as unlisted, from your own
   account, with the title, description, tags and thumbnail in `docs/video/UPLOAD.md` (the
   video is CC BY-SA 4.0), and paste the link into `docs/devpost.md` and the README. Wait for
   the status issue to say the cut was made again: the cut of Sep 25 still says the creek
   check's wording is draft, which is no longer true.

9. **By Fri Oct 2, 2 minutes, and one optional thing.** On GitHub, Settings, General, Social
   preview, upload `docs/social-preview.png`. Optional, 15 minutes each: blind labels. The gold
   labels came from the picks file you wrote with the planner, so they were not set blind to
   model output (`docs/deviations.md`, Sep 24). You, Rachel or both can label the 16 test photos
   without seeing the key: `uv run python scripts/label_photos.py --name alex --roles test` (or
   `--name rachel`) opens a local page and writes `photos/labels_<name>.csv`; commit it, or tell
   us it is there.

10. **Sat Oct 3, by 08:00: go public.** The second lock's job ran the evening before; check the
    status issue for its line first. Then follow `docs/SUBMISSION_DAY.md` in order: on `main`,
    `make go-public GO=dry`, then `make go-public GO=yes`. It scans the whole history for
    secrets, removes the working notes, runs the tests and `make submit-check`, checks the
    README's images and links, and only then makes the repository public, checks it logged out,
    and tags v1.0. This page, `docs/HANDOFF_NEXT.md` and `PLAN.md` stay, each marked as notes.
    From 09:00 that day nothing changes any more: the freeze, 36 hours before the deadline.

11. **Sun Oct 4, by 18:00: submit.** The organizers' deadline is 21:00. Before you press
    Submit, remove the report attached on Thursday and attach `docs/REPORT.pdf` from main again:
    the lock job rebuilt it on Fri Oct 2 with the second wave's rows.

Their sandbox's name, `sandbox.hl7europe.eu`, stopped resolving on Sep 23 (we reported it as
hl7-eu/oah issue 8) and came back on Sep 28; it has dropped out again since, so it comes and
goes. `/two` shows their lab record from the last copy the Mac fetched, and says when that was.
