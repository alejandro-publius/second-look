# Alex: what only you can do, in order

Everything on this page needs your voice, your eyes or your account. Everything else is done.
Times are Pacific.

Done for you on Sep 23 and 24: the two machine sittings are marked as tests (the public counts
read 0), the model ids and prices were confirmed and the paid AI run, four models from Sep 24, is
in the README (its cost is logged in `results/cost_log.jsonl`), and the QA key is set on the Worker with a copy as `QA_KEY` in
`~/second-look/.env` and `~/second-look-depth/.env`. Copy that key and your API key to your
password manager when you can. Nobody films at a creek: the creek shots are open footage from
Wikimedia Commons, already in the rough cut and credited in `docs/video/CREDITS.md`. Contributed
back: hl7-eu/oah pull request 5 and issues 6, 7 and 8 are open under your account. Two daily jobs
on this Mac are new: the OpenTimestamps anchor (06:00) and the iNaturalist cache (07:45).

1. **By Fri Sep 25, 20 minutes: record your voice.** Run `make video-rough` and play
   `docs/video/rough_cut_scratch_voice.mp4` once: its scratch voice is there for the timing
   only. Then record your voice against it, reading `docs/video/teleprompter.html` in a browser
   (space pauses, the arrows change speed). The words are the ones in `docs/video/VOICE_SCRIPT.md`
   and `docs/video/SHOTLIST.md`; beat 7 is filled from the real run. This is your only step in
   making the video.

2. **By Sat Sep 26, 20 minutes: Devpost.** Paste the fields from `docs/devpost.md` into the draft
   and invite Rachel to it. Pick the five gallery images it names, and attach `docs/REPORT.pdf`
   where Devpost takes a file. For the live judging, read `docs/submission/JUDGE_QA.md`: the 20
   hardest questions with honest answers.

3. **By Sat Sep 26 evening, 15 minutes: launch the panel study.** Make a researcher account on
   Prolific, add about 300 dollars, create the study from `docs/internal/PANEL_STUDY.md` (every
   field is written out there, the link and the completion code too) and publish it. The panel
   asks about ethics approval: its step 3 says what to check first. It runs by
   itself; `make panel-status` shows how many have finished.

4. **By Sat Sep 26, 2 minutes: the social preview.** On GitHub, Settings, General, Social preview,
   upload `docs/social-preview.png`.

5. **Optional, by Sat Sep 26, 15 minutes each: blind labels.** The gold labels came from the
   picks file you wrote with the planner, so they were not set blind to model output
   (`docs/deviations.md`, Sep 24). You, Rachel or both can label the 16 test photos without
   seeing the key: `uv run python scripts/label_photos.py --name alex --roles test` (or
   `--name rachel`) opens a local page and writes `photos/labels_<name>.csv`; commit it, or tell
   us it is there.

6. **By Sat Sep 26, and through Thu Oct 15: keep the Mac plugged in and awake.** On macOS 15:
   System Settings, Battery, Options, then turn on "Prevent automatic sleeping on power adapter when
   the display is off". Keep the lid open. The data lock (Sun Sep 27, 18:10 PDT), the uptime check
   every 10 minutes and the daily jobs run only while it is awake.

7. **Mon Sep 28: the dry-run submission.** Fill every Devpost field except the video, save, and
   read it back as a judge would. Judge mode opens that day; check `/demo` on your phone.

8. **By Tue Sep 29, 10 minutes: upload the video.** Upload the cut with your voice from your own
   account, with the licence line from `docs/devpost.md` in its description (the video is
   CC BY-SA 4.0), and paste the link into `docs/devpost.md` and the README.

9. **Wed Sep 30, morning: go public.** On `main`: `make go-public` to see what it will do, then
   `make go-public GO=yes`. It removes the working notes, runs `make submit-check`, and only then
   makes the repository public.

10. **Wed Sep 30, by 18:00: submit.**

Their sandbox's name, `sandbox.hl7europe.eu`, stopped resolving on Sep 23 (their own nameserver
answers that it does not exist); we reported it as hl7-eu/oah issue 8. While it is gone, `/two`
shows our record alone, and the sandbox re-push on Sep 28 cannot run.
