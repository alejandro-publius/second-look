# The jobs on the Mac, through Oct 15

UPDATE_30 section 7.4. Every dated or repeating job that keeps the live site and its data right
runs on this Mac through launchd, as Alex, from one checkout: `~/second-look-depth`. The table
below is `scripts/mac_jobs.py`, and `scripts/tests/test_mac_jobs.py` fails when the two differ.
`uv run python scripts/mac_jobs.py doc` writes the table from the script.
Each job logs under `~/second-look-backups/`, outside the repo. A job that runs while the Mac
sleeps is run when it wakes, but a Mac that is off or asleep all day misses the day, so the Mac
stays plugged in and awake through Oct 15 (`docs/ALEX_TODO.md`).

| Job | When (the Mac's own clock) | What it runs | Where it logs | The one command that shows it ran today |
|---|---|---|---|---|
| `com.secondlook.anchor` | daily at 06:00 | `scripts/anchor_audit_head.py`: stamps the audit log's last hash with OpenTimestamps, then upgrades every proof and writes results/ots.json | `~/second-look-backups/logs/anchor.log` | `uv run python scripts/mac_jobs.py ran-today anchor` |
| `com.secondlook.theirs` | daily at 07:30 | `scripts/cache_their_records.py`: one read only GET of the lab record /two shows, stored in D1 | `~/second-look-backups/logs/theirs.log` | `uv run python scripts/mac_jobs.py ran-today theirs` |
| `com.secondlook.inaturalist` | daily at 07:45 | `scripts/cache_inaturalist.py`: iNaturalist sightings of the listed invasive plants near each creek, stored in D1 | `~/second-look-backups/logs/inaturalist.log` | `uv run python scripts/mac_jobs.py ran-today inaturalist` |
| `com.secondlook.repush` | daily at 08:00 | `scripts/sandbox_retry.py`: asks whether their sandbox's name resolves; when it does, puts the Library entry and the golden visit back by conditional create and refreshes /two's cache | `~/second-look-backups/logs/repush.log` | `uv run python scripts/mac_jobs.py ran-today repush` |
| `com.secondlook.hl7` | daily at 09:00 | `scripts/hl7_watch.py`: reads hl7-eu/oah pull request 5 and issues 6, 7 and 8 with gh; a new maintainer comment goes to the status issue. It never replies | `~/second-look-backups/logs/hl7.log` | `uv run python scripts/mac_jobs.py ran-today hl7` |
| `com.secondlook.backup` | daily at 21:00, and at wake if the Mac slept through it | `scripts/backup_d1.sh`: exports the D1 study database to ~/second-look-backups, outside the repo | `~/second-look-backups/logs/backup.log` | `uv run python scripts/mac_jobs.py ran-today backup` |
| `com.secondlook.uptime` | every 10 minutes | `scripts/uptime.py`: GETs six pages of the live site; two failures in a row write uptime.log, comment on the status issue once and show a notification | `~/second-look-backups/logs/uptime.out` | `uv run python scripts/mac_jobs.py ran-today uptime` |
| `com.secondlook.lock` | once, at 2026-09-28T01:10:00Z (Sep 27, 18:10 PDT) | `scripts/lock_analysis.py`: the data lock: backup, export, the one pre-registered analysis, the README's human row, make check, commit, deploy, push, and a line on the status issue | `~/second-look-backups/lock.log` | `uv run python scripts/mac_jobs.py ran-today lock` |
| `com.secondlook.lock2` | once, at 2026-10-03T04:10:00Z (Oct 2, 21:10 PDT) | `scripts/lock_analysis.py --wave 2`: the second data lock, for the second wave: backup, export, the two registered analyses once on the second window, the second wave's own README rows, make check, commit, deploy, push, and a line on the status issue | `~/second-look-backups/lock.log` | `uv run python scripts/mac_jobs.py ran-today lock2` |

`uv run python scripts/mac_jobs.py today` prints all nine lines at once (`make mac-jobs-today`).
"Ran today" means the job's log was written today by the Mac's calendar; for the uptime job it
means in the last 25 minutes. A log only says a job started: read its last lines for what it did.

Where else they write: the uptime job writes an outage to `~/second-look-backups/uptime.log`;
the sandbox, uptime and hl7 jobs keep what they saw last in `~/second-look-backups/state/`; the
lock job keeps a copy of the exported study tables in `~/second-look-backups/lock-<time>/`. In the
checkout, only the anchor job (`proofs/`, `results/ots.json`) and the re-push
(`fhir/sandbox_ledger.jsonl`) write files, and they commit nothing. The lock job refuses any other
local change; it sets exactly those files aside while it checks, commits and deploys, so the site
is built from what is committed, and puts them back at the end. If `origin/depth` brought a newer
copy of one meanwhile, that copy stands and the job's own goes to
`~/second-look-backups/set-aside-<time>/`, so nothing is lost.

The audit log is the one file with a rule of its own. When the partner's sandbox answers, the
re-push job adds a `sandbox_push` line to `audit/log.jsonl` in the checkout and commits nothing.
The first run of the lock job refused that change, so on Sep 29 the line had to be committed by
hand before the job could run. The second run carries such lines: when the only change to the
audit log is lines added at its end, of the kind the re-push job writes, and the chain holds,
the lines stay in the log, in their place, and go into the lock's commit ahead of its own
`data_lock` line. A proof the anchor job made of such a line stays good, because the line is
kept as written. Only if `origin/depth` added lines of its own meanwhile are the carried lines
chained again after those, with their own time, kind and payload hash; the lines as written
are then kept in `~/second-look-backups/set-aside-<time>/`. Any other change to the audit log is
refused by name, as before.

## Install, once, from the checkout the jobs run from

The jobs today still run from `~/second-look-depth` at an old commit (the backup from
`~/second-look`), and the new scripts are not there yet. In this order:

1. Fast-forward `~/second-look-depth` to `origin/depth` once this work is merged, and leave it on
   `depth` with no other local change: `git -C ~/second-look-depth status` shows at most the
   anchor job's `proofs/` and `results/ots.json` and the ledger.
2. From that checkout: `make mac-jobs-install`. It writes every plist above to
   `~/Library/LaunchAgents/` for `~/second-look-depth` (`JOBS_ROOT=... make mac-jobs-install` for
   another checkout), loads each with launchctl, and refuses a checkout that lacks a job's script.
   `make lock-analysis-install` installs the lock job alone.
3. Check: `uv run python scripts/mac_jobs.py check-installed` exits 0 when every plist is the one
   the table writes for `~/second-look-depth` and launchd has it loaded.
4. Before Sep 27, 18:10 PDT: `make lock-analysis-ready` exits 0 when nothing would stop the lock
   job: the branch, local changes, the tools `make check` needs, the wrangler and gh logins, the
   QA key in `.env`, and a production deploy recorded in `docs/notes/hosting.md` with its files
   kept, so a failure has something to go back to. Deploy once with the new `scripts/deploy.sh`
   before then, or that last check fails.
5. The second run, for the second wave (`docs/analysis_plan_v3.md`). Once this work is on
   `origin/depth` and `~/second-look-depth` is fast-forwarded to it:
   `make lock-analysis-2-install` installs the job `lock2` alone, for Oct 2 at 21:10 PDT, which
   is 2026-10-03T04:10:00Z. Before then, `make lock-analysis-2-ready` exits 0 when nothing would
   stop it. It asks what step 4 asks, and it lets lines the re-push job added to the audit log
   pass. It also asks the second wave's analysis what it would refuse for once the lock has
   passed: the tag `prereg-v3` missing from the checkout, the script not pinned to the tag, or a
   plan or a script that differs from the tagged one.

The five one-job installers (`scripts/install_*_job.sh`) still work and install the same plists;
`make mac-jobs-install` is the one to use.

## If a job did not run

- Asleep or off: the Mac missed it. Run the script in the table's third column by hand from
  `~/second-look-depth` (`make lock-analysis` for the lock and `make lock-analysis-2` for its
  second run; each refuses before its lock and runs once only).
- Not loaded: `make mac-jobs-install` again, then `check-installed`.
- The lock job failed: it says why on the status issue and in `~/second-look-backups/lock.log`,
  and it has already put production and the checkout back. Fix the cause, then
  `make lock-analysis`, or `make lock-analysis-2` for the second run.
- The site is down: the uptime job has said so on the status issue. `make rollback` shows the way
  back to the last good deploy; `make rollback ROLLBACK=yes` takes it.
