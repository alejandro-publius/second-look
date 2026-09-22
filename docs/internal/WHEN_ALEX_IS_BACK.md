# When Alex is back

Ten steps, in order. Each is something only you can do: your eyes, your login, your key, your voice, your creek, your decision. Everything software could do is done or waiting in a pull request.

| # | Step | Command or place | Minutes |
|---|---|---|---|
| 1 | Look at the live site on your phone. The cloud session could not reach it. `/demo` should say Judge mode opens on Sep 28. | https://second-look-79t.pages.dev/judges and https://second-look-79t.pages.dev/demo | 2 |
| 2 | Mark the two machine sittings in the live table as tests (your Cloudflare login). Look first, then change, as `docs/ALEX_TODO.md` on main says. | `cd ~/second-look/worker && npx wrangler d1 execute second-look --remote --command "SELECT id, is_test, started_at FROM session WHERE is_test = 0"` | 5 |
| 3 | Decide on the model gate. `docs/notes/model_ids.md` says the ids and prices were checked on Sep 21, but `evals/models.yaml` and `evals/pricing.yaml` still say unconfirmed, so the paid run refuses. If you agree, tell a session: "I confirm the ids and prices in docs/notes/model_ids.md. Flip the flags and update the two tests that expect them unconfirmed." | a Claude Code session on `~/second-look-depth` | 5 |
| 4 | Run the AI on the 16 photos with your key (Batch API, tens of cents per `docs/notes/model_ids.md`). | `cd ~/second-look-depth && uv run python evals/model_sweep.py --real` | 15 |
| 5 | Read and merge the pull requests into depth: #6 (takeover) and #5 (the kits, draft). | https://github.com/alejandro-publius/second-look/pulls | 10 |
| 6 | Thirty minutes at Strawberry Creek, including one real creek check in the app. | `docs/video/CREEK_30_MIN.md` | 40 |
| 7 | Record your voice against the teleprompter. Fill the one slot from step 4's result first. | open `docs/video/teleprompter.html`, script in `docs/video/VOICE_SCRIPT.md` | 20 |
| 8 | Paste the Devpost fields and invite Rachel to the draft. Paste the video link when it exists. | `docs/submission/DEVPOST_PASTE.md` | 20 |
| 9 | After data lock (2026-09-28T01:00:00Z): merge depth into main and deploy, in the order in `docs/notes/hosting.md`, phone tests after each step. Then the dry-run submission on Sep 28. | `docs/notes/hosting.md`, "The merge, after data lock" | 45 |
| 10 | Sep 30: make the repo public, open the pull request to their guide, submit by 6pm. | `bash scripts/go_public.sh --run` on main, then `docs/internal/upstream/README.md` | 30 |
