# Alex: what only you can do, in order

Everything on this page needs your voice, your eyes or your account. Everything else is done.
Times are Pacific.

Done for you on Sep 23 and 24: the two machine sittings are marked as tests (the public counts
read 0), the model ids and prices were confirmed and the paid AI run, four models from Sep 24, is
in the README (its cost is logged in `results/cost_log.jsonl`), and the QA key is set on the Worker with a copy as `QA_KEY` in
`~/second-look/.env` and `~/second-look-depth/.env`. Copy that key and your API key to your
password manager when you can. Nobody films at a creek: the creek shots are open footage from
Wikimedia Commons, already in the rough cut and credited in `docs/video/CREDITS.md`.

1. **Tonight, 2 minutes: look at the live site on your phone.** `/`, `/walk`, `/judges`, and
   `/demo`, which says Judge mode opens on Sep 28. https://second-look-79t.pages.dev

2. **By Fri Sep 25, 20 minutes: record your voice.** Run `make video-rough` and play
   `docs/video/rough_cut_scratch_voice.mp4` once: its scratch voice is there for the timing
   only. Then record your voice against it, reading `docs/video/teleprompter.html` in a browser
   (space pauses, the arrows change speed). The words are the ones in `docs/video/VOICE_SCRIPT.md`
   and `docs/video/SHOTLIST.md`; beat 7 is filled from the real run. This is your only step in
   making the video.

3. **By Sat Sep 26, 20 minutes: Devpost.** Paste the fields from `docs/devpost.md` into the draft
   and invite Rachel to it. Pick the five gallery images it names. For the live judging, read
   `docs/submission/JUDGE_QA.md`: the 20 hardest questions with honest answers.

4. **Sun Sep 28: the dry-run submission.** Fill every Devpost field except the video, save, and
   read it back as a judge would. Judge mode opens that day; check `/demo` on your phone.

5. **By Tue Sep 29, 10 minutes: upload the video.** A session lays your voice over the rough cut
   in place of the scratch voice, keeping every credit line and the end card. The upload must come
   from your account: put the licence line from `docs/devpost.md` in its description (the video is
   CC BY-SA 4.0), and paste the link into `docs/devpost.md` and the README, or give it to a session.

6. **Wed Sep 30, morning: go public.** On `main`: `make go-public` to see what it will do, then
   `make go-public GO=yes`. It removes the working notes, runs `make submit-check`, and only then
   makes the repository public. Then, 10 minutes, open the example pull request to their guide:
   in `~/second-look-depth`, `docs/internal/upstream/README.md` has every command.

7. **Wed Sep 30, by 18:00: submit.**

If you want to, and only you can decide it: their sandbox's name, `sandbox.hl7europe.eu`, stopped
resolving on Sep 23 (their own nameserver answers that it does not exist). While it is gone, `/two`
shows our record alone, and the sandbox re-push on Sep 28 cannot run. Telling the OneAquaHealth
team is your call.
