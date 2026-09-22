# Alex, today (checklist)

DRAFT, written 2026-09-20 by Claude Code. Tick each line when done. Every command runs from the repo folder `~/second-look` unless it says otherwise.

## Accounts and logins (needed before `make deploy`)

- [ ] `gh auth status` (if it says not logged in: `gh auth login`)
- [ ] `brew install flyctl && fly auth login` (Fly.io account with a payment method; the API machine costs under 5 dollars through Oct 15)
- [ ] `npm i -g vercel && vercel login` (Vercel Hobby account)
- [ ] Then deploy with one command: `make deploy`. It needs `DATABASE_URL` set for production; the script tells you if something is missing.

## Money

- [ ] Anthropic console: set a monthly spend limit and an email alert (Settings, then Limits). The budget for this project is a few dollars.
- [ ] Put `ANTHROPIC_API_KEY` in `.env` only (copy `.env.example` to `.env` first). Never export it in a shell where Claude Code is running. Never commit `.env`.
- [ ] If the key is in `.env` and probe photos exist, the P3 probe may spend about 1 dollar. Nothing else spends money; every other model call uses the fake client.

## Photos and probes

- [ ] Probe photos (a handful of real creek JPEGs for the model probe) go in `data/probe/`. Create it with `mkdir -p data/probe`. Everything under `data/` is gitignored, so originals never enter the repo.
- [ ] Rachel's originals go through `uv run python scripts/ingest_photos.py --help` (it strips EXIF location data, resizes, and writes manifest rows). Originals stay out of the repo.
- [ ] Your own blind labels: `uv run python scripts/label_photos.py --name alex`. Do not open `labels_rachel.csv`.
- [ ] Strawberry Creek trip: the shot list is in `docs/team_pack.md`. Also record video footage and do one assessment in the official OneAquaHealth app with a screenshot of every screen. Keep the screenshots in `data/app_screenshots/` (gitignored) and write which form items you verified in `docs/notes/app_wording.md`.

## The sandbox write test

- [ ] Already done: K6 passed on 2026-09-20 (create 201, read 200, delete 200, read after delete 410). Evidence: `docs/notes/sandbox_write_test.txt`.
- [ ] Only if asked to run it again: `bash scripts/sandbox_write_test.sh | tee docs/notes/sandbox_write_test.txt`. Each run writes one tagged record to the shared sandbox and deletes that one id. Never delete anything there by hand.

## Logging a kill test result

Add one row to the table in `docs/KILL_TESTS.md`:

`| K<n> | <what the test checks> | PASS or FAIL <UTC date and time>: <one line of what happened> | <path to the evidence file> |`

Evidence is a file in the repo (a saved output under `docs/notes/`, a results file, a ledger line). Never a number typed from memory.

## Posters

- [ ] `make poster` writes the Letter and A4 PDFs to `apps/web/out/`. That folder is gitignored, so print from there. The poster carries a QR code to `?src=poster` and shows no answer.

## The launch gate

- [ ] `make preflight` prints every failed check. Read each reason:
  - HUMAN: an input only a person can supply (photos, labels, question wording, approved copy, app items verified against your screenshots, the `prereg-v1` tag). Expected to fail until the inputs land. Fix by supplying the input.
  - BUILD: anything else (a test, a hash, a missing file, a broken command). Paste the line to Claude Code. A preflight that fails for human reasons only is the goal.
- [ ] `make submit-check` is the submission gate. Before Sep 30 it should fail only on: video link, public repo, real results.

## Notes only you can write

- [ ] `docs/notes/devpost_fields.md`: paste every field of the Devpost "Create project" form (names, limits, required or not), and whether a one-person team is refused. The hackathon page lists "Team required" under who can participate, so add Rachel as a teammate on Devpost before Sep 28. `docs/devpost.md` maps each field to a README section once you paste them.
- [ ] `docs/notes/slack.md`: join the hackathon Slack; save the channel list, the pinned posts, and any link to an official data set or a workshop recording.
- [ ] `docs/notes/their_image_model.md`: watch OneAquaHealth's ten-minute AI image model video and write five lines: what it classifies, on which photos, whether it is live in the app, what it gets wrong, what that means for our checker.
- [ ] The consent contact email: give it to Claude Code to put in `content/locales/en.json` under `consent.contact`. Wanted by Mon Sep 21, 18:00.

## Recruiting, from Wed Sep 23

- [ ] Messages are ready in `docs/recruiting_messages.md`. Replace the site URL first. Each link carries its own `?src=` so `GET /api/test/counts` tells you where people came from.
- [ ] Check names and contacts of creek groups yourself (for example Friends of Five Creeks and the campus office that looks after Strawberry Creek). Post posters only where posting is allowed.
- [ ] One creek visitor on camera taking the test, ideally someone walking a dog there, with `docs/release_form.md` signed.
