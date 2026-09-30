# Going public on Sat Oct 3, submitting on Sun Oct 4

The exact order for going public and submitting, with the command for each step and what to
check after it. Times are Pacific (PDT). The organizers moved the deadline to Sun Oct 4 at 21:00
(read from Devpost on Sep 29, `docs/internal/updates/UPDATE_33.md`). The repository goes public
on the morning of Sat Oct 3, the day before the deadline day, and nothing changes after 09:00
that day: the freeze, 36 hours before the deadline. We submit on Sun Oct 4 by 18:00.

The second wave of the study locks on Fri Oct 2 at 21:00, and its job runs at 21:10: it runs
the analysis once, fills the README's rows for that wave, deploys and pushes. Going public comes
after it. The job puts a notice on the Mac's screen either way. At 21:50 on Friday look for
"Second data lock done" on the status issue; if it is not there, run `make lock-analysis-2` in
`~/second-look-depth` that night and wait for it (about 30 minutes), so Saturday morning is free.
Run nothing heavy on the Mac from 21:00 to 22:00 on Friday. Before 21:00, if
`~/second-look-backups/logs/repush.log` says their sandbox answered this week, commit
`fhir/sandbox_ledger.jsonl` on depth by hand.

`make go-public` can be run from any Claude Code window on the Mac. Open one in `~/second-look`
(the checkout on `main`) and paste the command; nothing else is needed. The Mac needs `gh`
logged in as alejandro-publius, `gitleaks` (`brew install gitleaks`) and `uv`, which it has.

What `make go-public` does is in `scripts/go_public.py`, at the top. In short: `GO=dry` runs
every step before the flip in a throwaway copy and stops, so it never changes `main`;
`GO=yes` runs them all on `main`, and every step before the flip is safe to run again.

## Thu Oct 1: the dry-run submission (about 45 minutes)

A full rehearsal on Devpost, saved as a draft and not submitted.

| Time | Step | Command or place | Check after it |
|---|---|---|---|
| 10:00 | Start from `main` | `cd ~/second-look && git switch main && git pull --ff-only && make submit-check` | The last line is `submit-check: 2 failed: video_link, repo_public`. Anything else failing is ours to fix first. |
| 10:10 | Fill every Devpost field | The Devpost draft, pasting from `docs/devpost.md`, one code block per field, in its order | Every field holds the current text; the description starts with the track statement. The video field stays empty until the video is uploaded. |
| 10:25 | Attach the report | Devpost's file field: `docs/REPORT.pdf` | The file shows on the draft with its name. |
| 10:30 | Gallery and team | The five images `docs/devpost.md` lists, in its order; invite Rachel Selbrede | Five images in order; Alex Velazquez and Rachel Selbrede both on the team. |
| 10:35 | Save the draft | Devpost's Save button, not Submit | The draft page says it is saved. |
| 10:40 | Read it on a phone | The draft, on a phone, top to bottom, as a judge would | Every field whole, no raw Markdown where Devpost shows plain text, every link opens. Fix anything wrong in `docs/devpost.md`, then run `make submit-check` again. |
| 10:50 | Rehearse go-public | `make go-public GO=dry` (about 6 minutes) | Seven lines, then `go-public: 7 steps, ... failed: ...; stopped before the push and the flip`. Today `submit` fails on the video link, which is expected; any other FAIL gets fixed now. `changelog` fails if a day with commits has no line in `CHANGELOG.md`: add it. |

## By Fri Oct 2: the video link

Upload the video and paste its link into `README.md` and `docs/devpost.md` (step 8 in
`docs/ALEX_TODO.md`). Check: `make submit-check` ends `submit-check: 1 failed: repo_public`.

## Sat Oct 3, in order: go public before the freeze at 09:00

| Time | Step | Command | Check after it |
|---|---|---|---|
| 07:30 | Start from `main` | `cd ~/second-look && git switch main && git pull --ff-only && git status` | `git status` says the tree is clean. `gh run list --branch main --limit 1` shows the newest run completed with success. |
| 07:35 | The changelog | Add a `### <day>` line to `CHANGELOG.md` for each day with commits since its last one, in plain words; commit and push to `main` | `git log -1` shows the commit; the push printed no error. |
| 07:45 | The submission gate | `make submit-check` | The last line is `submit-check: 1 failed: repo_public`. If `video_link` is there too, the link is missing: paste it first. |
| 07:50 | Rehearse | `make go-public GO=dry` (about 6 minutes) | Every line is PASS or SKIP, and the last is `go-public: 7 steps, 0 failed: none; stopped before the push and the flip, as GO=dry does`. `main` is unchanged. |
| 08:00 | Go public | `make go-public GO=yes` (about 8 minutes) | Twelve lines, each PASS or SKIP, then `go-public: alejandro-publius/second-look is public, tagged v1.0 and released`. |
| 08:10 | Look as a stranger | A private tab on a phone: https://github.com/alejandro-publius/second-look | The README shows with its pictures and the CI badge, and the working notes folder is gone. The v1.0 release is on the Releases page. https://second-look-79t.pages.dev opens. |
| 08:15 | CI on the public repo | `gh run list --branch main --limit 1` (again after about 15 minutes) | The run for the go-public commit completed with success. |
| 08:35 | The gate, all green | `make submit-check` | The last line is `submit-check: 0 failed: none`. |

## Sun Oct 4, in order: submit by 18:00

| Time | Step | Command | Check after it |
|---|---|---|---|
| 10:00 | The gate, once more | `cd ~/second-look && git switch main && git pull --ff-only && make submit-check` | The last line is `submit-check: 0 failed: none`. `main` is the commit that went public, plus nothing. |
| 10:10 | Submit | The saved Devpost draft: paste the video link and any field that changed since Oct 1 (compare with `docs/devpost.md`), remove the attached report and attach `docs/REPORT.pdf` from main again (the lock job rebuilt it on Fri Oct 2 with the second wave's rows), check Rachel is on the team, then Submit | Devpost shows the project as submitted to the OneAquaHealth hackathon. |
| 10:25 | Record the page | Put the project's devpost.com/software link in `docs/devpost.md`, commit and push. It is the one change after the freeze, and it changes no code | `uv run python scripts/done_items.py devpost-submitted` ends `done-item devpost-submitted: ok`. |

## If a step says FAIL

Fix what its line names, then run the same command again. Every step before the flip is safe
to repeat: the notes commit is made once and then skipped. After the flip, `flip`, `tag` and
`release` skip themselves when they are already done, so a second `make go-public GO=yes` only
finishes what is left.

| Step | What its FAIL means | What to do |
|---|---|---|
| start | Not on `main`, the tree is not clean, or `main` is behind GitHub | `git switch main`, commit or undo the changes, `git pull --ff-only` |
| secrets | gitleaks or the tree scan found something that looks like a key | If it is a made-up test value, add its fingerprint to `.gitleaksignore` with a reason. If it is a real key: stop, revoke the key, and ask. History is never rewritten (hard rule 15). |
| notes | A tracked file still names the working notes | Reword the file the line names |
| tests | `make lint` or a Python test failed on the tree without the notes | Fix what the line names |
| submit | `make submit-check` failed on more than the repo being private | Fix the named check: usually the video link or a Devpost field |
| readme | An image, a link or a heading in the README does not answer | Fix the README |
| changelog | A day with commits has no line in `CHANGELOG.md` | Add the line |
| push | GitHub refused the push | `git pull --ff-only`, then run again |
| flip | `gh` could not make the repo public | `gh auth status` must show the `repo` scope |
| public | A stranger could not load the page, an image, the badge or the live link | GitHub can take a few minutes after the flip: wait five and run `make go-public GO=yes` again |
| tag, release | The tag or the release was not made | Run `make go-public GO=yes` again. It never moves a v1.0 that names another commit. |

If Alex cannot run it on the morning of Oct 3, any Claude Code window on the Mac can: the same
commands, in the same order, from `~/second-look`.
