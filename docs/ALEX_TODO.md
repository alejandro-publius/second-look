# Alex: what only you can do, in order

Everything on this page needs your hands, your voice, your key or your account. Everything else
is done. Times are Pacific.

1. **Now, 5 minutes: mark the two machine sittings as tests.** Our own checks left them in the live
   study table, and reading or changing that table is not allowed from the terminal. Look, then
   change:

   ```
   cd ~/second-look/worker
   npx wrangler d1 execute second-look --remote --command "SELECT id, arm, is_test, started_at, completed_at FROM session WHERE is_test = 0"
   npx wrangler d1 execute second-look --remote --command "UPDATE session SET is_test = 1 WHERE is_test = 0 AND started_at < '2026-09-22T17:33:00Z'"
   ```

   Afterwards `curl -s https://second-look-api.thealexschroeder.workers.dev/api/test/counts` shows 0.

2. **Now, 5 minutes: the model run.** Your decision first: `evals/models.yaml` and
   `evals/pricing.yaml` still say unconfirmed, and they are what licenses spending money. The ids
   and prices were checked on Sep 21 and again on Sep 22 (`docs/notes/model_ids.md`). If you agree,
   flip the flags to true. Then put your key in `~/second-look-depth/.env` as
   `ANTHROPIC_API_KEY=...` and run `cd ~/second-look-depth && make ai-run`. It spends at most
   40 dollars, through the Batch API, and writes every AI result to `results/`; the next session
   fills the README's AI table from those files.

3. **Done on Sep 23 by the session: the QA key.** A fresh key is set on the Worker, and a copy
   is `QA_KEY` in `~/second-look/.env` and `~/second-look-depth/.env` (both ignored by git). Copy
   it to your password manager when you can. With it, the full phone sitting against production
   runs as a test: `set -a; . ./.env; set +a; SITE_URL=https://second-look-79t.pages.dev node apps/web/scripts/live-check.mjs`.

4. **By Thu Sep 24, 40 minutes: the creek visit.** 30 minutes at Strawberry Creek with the shot list in
   `docs/video/RECORD_AT_THE_CREEK.md`. Anyone on camera signs `docs/release_form.md` first. File
   one real creek check with `/check` while you are there; it replaces the worked example in the
   README.

5. **By Fri Sep 25, 20 minutes: your voice.** Fill beat 7's slot from the model run first. Open
   `docs/video/teleprompter.html` in a browser (space pauses, the arrows change speed) and read
   the words in `docs/video/VOICE_SCRIPT.md`, the same words as `docs/video/SHOTLIST.md`. The rough
   cut (`make video-rough`, then play `docs/video/rough_cut_scratch_voice.mp4`) has a scratch voice
   for timing only.

6. **By Sat Sep 26, 20 minutes: Devpost.** Paste the fields from `docs/devpost.md` into the draft and invite
   Rachel to it. Pick the five gallery images it names. For the live judging, read
   `docs/submission/JUDGE_QA.md`: the 20 hardest questions with honest answers.

7. **Sun Sep 28: the dry-run submission.** Fill every Devpost field except the video, save, and
   read it back as a judge would. Judge mode opens that day; check `/demo` on your phone.

8. **By Tue Sep 29: the video.** Cut your voice and creek footage into the rough cut, upload it,
   and put the link in `docs/devpost.md` and the README.

9. **Wed Sep 30, morning: go public.** On `main`: `make go-public` to see what it will do, then
   `make go-public GO=yes`. It removes the working notes, runs `make submit-check`, and only then
   makes the repository public. Then, 10 minutes, open the example pull request to their guide:
   in `~/second-look-depth`, `docs/internal/upstream/README.md` has every command.

10. **Wed Sep 30, by 18:00: submit.**
