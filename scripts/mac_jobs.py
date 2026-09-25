"""Every launchd job on the Mac, in one table, with one installer and one check for each.

docs/internal/MAC_JOBS.md is written from this table and a test keeps the two the same. The jobs
run as Alex from one checkout, `~/second-look-depth` by default, and log under
`~/second-look-backups/`. The lock job (scripts/lock_analysis.py) reads `writes` to know which
files in its checkout the other jobs may have changed, and leaves those alone.

  uv run python scripts/mac_jobs.py install [--root ~/second-look-depth] [--only NAME] [--dry-run]
  uv run python scripts/mac_jobs.py check-installed [--root ...]   exit 0 when every plist is
                                                                  the one this table writes, loaded
  uv run python scripts/mac_jobs.py ran-today NAME                 exit 0 when its log moved today
  uv run python scripts/mac_jobs.py today                          all of them, one line each
"""

from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path("~/second-look-depth")
BACKUPS = Path("~/second-look-backups")
# When the lock job fires: ten minutes after the data lock (core/lock.py), so the Mac's clock
# may be a few minutes off and the analysis still never runs before the lock.
LOCK_JOB_UTC = datetime(2026, 9, 28, 1, 10, tzinfo=UTC)


@dataclass(frozen=True)
class Job:
    name: str
    when: str
    what: str
    command: tuple[str, ...]
    log: str
    err: str
    calendar: dict[str, int] | None = None
    interval: int | None = None
    writes: tuple[str, ...] = field(default=())
    shows_it_ran: str = ""
    # A job that runs all day counts as running only if its log moved this many minutes ago.
    recent_minutes: int | None = None

    @property
    def label(self) -> str:
        return f"com.secondlook.{self.name}"

    def script(self) -> str:
        """The repo file the job runs, which the checkout must hold before it is installed."""
        words = " ".join(self.command).replace(";", " ").split()
        return next(p for p in words if p.startswith("scripts/"))

    def ran_file(self) -> str:
        return self.shows_it_ran or self.log


def lock_calendar(tz: tzinfo | None = None) -> dict[str, int]:
    """The lock job's time as the Mac's own clock reads it; launchd has no time zones."""
    local = LOCK_JOB_UTC.astimezone(tz)
    return {"Month": local.month, "Day": local.day, "Hour": local.hour, "Minute": local.minute}


def uv_run(script: str) -> tuple[str, ...]:
    return ("uv", "run", "python", script)


def jobs(tz: tzinfo | None = None) -> tuple[Job, ...]:
    return (
        Job(
            "anchor",
            "daily at 06:00",
            "stamps the audit log's last hash with OpenTimestamps, then upgrades every proof and "
            "writes results/ots.json",
            (
                "bash",
                "-c",
                "uv run python scripts/anchor_audit_head.py; uv run python scripts/ots_status.py",
            ),
            "logs/anchor.log",
            "logs/anchor.err",
            calendar={"Hour": 6, "Minute": 0},
            writes=("proofs/", "results/ots.json"),
        ),  # fmt: skip
        Job(
            "theirs",
            "daily at 07:30",
            "one read only GET of the lab record /two shows, stored in D1",
            uv_run("scripts/cache_their_records.py"),
            "logs/theirs.log",
            "logs/theirs.err",
            calendar={"Hour": 7, "Minute": 30},
        ),
        Job(
            "inaturalist",
            "daily at 07:45",
            "iNaturalist sightings of the listed invasive plants near each creek, stored in D1",
            uv_run("scripts/cache_inaturalist.py"),
            "logs/inaturalist.log",
            "logs/inaturalist.err",
            calendar={"Hour": 7, "Minute": 45},
        ),
        Job(
            "repush",
            "daily at 08:00",
            "asks whether their sandbox's name resolves; when it does, puts the Library entry and "
            "the golden visit back by conditional create and refreshes /two's cache",
            uv_run("scripts/sandbox_retry.py"),
            "logs/repush.log",
            "logs/repush.err",
            calendar={"Hour": 8, "Minute": 0},
            writes=("fhir/sandbox_ledger.jsonl",),
        ),
        Job(
            "hl7",
            "daily at 09:00",
            "reads hl7-eu/oah pull request 5 and issues 6, 7 and 8 with gh; a new maintainer "
            "comment goes to the status issue. It never replies",
            uv_run("scripts/hl7_watch.py"),
            "logs/hl7.out",
            "logs/hl7.err",
            calendar={"Hour": 9, "Minute": 0},
            shows_it_ran="logs/hl7.log",
        ),
        Job(
            "backup",
            "daily at 21:00, and at wake if the Mac slept through it",
            "exports the D1 study database to ~/second-look-backups, outside the repo",
            ("bash", "scripts/backup_d1.sh"),
            "logs/backup.log",
            "logs/backup.err",
            calendar={"Hour": 21, "Minute": 0},
        ),
        Job(
            "uptime",
            "every 10 minutes",
            "GETs six pages of the live site; two failures in a row write uptime.log, comment on "
            "the status issue once and show a notification",
            uv_run("scripts/uptime.py"),
            "logs/uptime.out",
            "logs/uptime.err",
            interval=600,
            recent_minutes=25,
        ),
        Job(
            "lock",
            "once, at 2026-09-28T01:10:00Z (Sep 27, 18:10 PDT)",
            "the data lock: backup, export, the one pre-registered analysis, the README's human "
            "row, make check, commit, deploy, push, and a line on the status issue",
            uv_run("scripts/lock_analysis.py"),
            "logs/lock.out",
            "logs/lock.err",
            calendar=lock_calendar(tz),
            shows_it_ran="lock.log",
        ),
    )


JOBS = jobs()


def by_name(name: str) -> Job:
    for job in JOBS:
        if job.name == name:
            return job
    raise SystemExit(
        f"mac-jobs: no job called {name}; the jobs are {', '.join(j.name for j in JOBS)}"
    )


def mac_job_files() -> tuple[str, ...]:
    """Paths in the checkout the jobs write; a path ending in / means everything under it."""
    return tuple(p for job in JOBS for p in job.writes)


def expand(path: Path, home: Path) -> Path:
    text = str(path)
    return home / text[2:] if text.startswith("~/") else path


def program(job: Job, root: Path, uv: str) -> list[str]:
    """ProgramArguments: uv by its full path and every script by its full path in the checkout."""
    if job.command[0] == "uv":
        return [uv, *job.command[1:3], str(root / job.command[3])]
    if job.command[:2] == ("bash", "-c"):
        return ["/bin/bash", "-c", job.command[2].replace("uv run", f"'{uv}' run")]
    return ["/bin/bash", str(root / job.command[1])]


def plist(job: Job, root: Path, home: Path, uv: str) -> dict[str, Any]:
    backups = expand(BACKUPS, home)
    doc: dict[str, Any] = {
        "Label": job.label,
        "ProgramArguments": program(job, root, uv),
        "WorkingDirectory": str(root),
        "RunAtLoad": False,
        "StandardOutPath": str(backups / job.log),
        "StandardErrorPath": str(backups / job.err),
        "EnvironmentVariables": {
            "PATH": f"{home}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
        },
    }
    if job.calendar is not None:
        doc["StartCalendarInterval"] = job.calendar
    if job.interval is not None:
        doc["StartInterval"] = job.interval
    return doc


def plist_path(job: Job, home: Path) -> Path:
    return home / "Library" / "LaunchAgents" / f"{job.label}.plist"


def domain() -> str:
    return f"gui/{os.getuid()}"


def install(
    root: Path, home: Path, uv: str, only: str | None = None, dry_run: bool = False
) -> list[str]:
    """Write each plist and load it. Refuses a checkout that lacks a job's script."""
    chosen = [by_name(only)] if only else list(JOBS)
    missing = [j.script() for j in chosen if not (root / j.script()).is_file()]
    if missing:
        raise SystemExit(
            f"mac-jobs: {root} has no {', '.join(missing)}; fast-forward it to origin/depth first"
        )
    lines = []
    backups = expand(BACKUPS, home)
    for job in chosen:
        data = plistlib.dumps(plist(job, root, home, uv))
        path = plist_path(job, home)
        if dry_run:
            lines.append(f"mac-jobs: would write {path} ({job.when})")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        (backups / "logs").mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if shutil.which("plutil"):
            subprocess.run(["plutil", "-lint", str(path)], check=True, capture_output=True)
        subprocess.run(["launchctl", "bootout", f"{domain()}/{job.label}"], capture_output=True)
        subprocess.run(["launchctl", "bootstrap", domain(), str(path)], check=True)
        lines.append(f"mac-jobs: {job.label} installed, {job.when}, from {root}")
    return lines


def check_installed(root: Path, home: Path, uv: str) -> list[str]:
    problems = []
    for job in JOBS:
        path = plist_path(job, home)
        if not path.is_file():
            problems.append(f"{job.label}: no plist at {path}")
            continue
        if plistlib.loads(path.read_bytes()) != plist(job, root, home, uv):
            problems.append(f"{job.label}: the plist is not the one this table writes for {root}")
        loaded = subprocess.run(
            ["launchctl", "print", f"{domain()}/{job.label}"], capture_output=True
        )
        if loaded.returncode != 0:
            problems.append(f"{job.label}: not loaded in launchd")
    return problems


def ran_today(job: Job, home: Path, now: datetime | None = None) -> tuple[bool, str]:
    """Whether the job's log was written today, by the Mac's own calendar."""
    path = expand(BACKUPS, home) / job.ran_file()
    if not path.exists():
        return False, f"{job.name}: {path} does not exist yet"
    written = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    now = now or datetime.now().astimezone()
    stamp = written.strftime("%Y-%m-%d %H:%M")
    if job.recent_minutes is not None:
        age = (now - written).total_seconds() / 60
        if 0 <= age <= job.recent_minutes:
            return True, f"{job.name}: running, {path.name} written at {stamp}"
        return (
            False,
            f"{job.name}: {path.name} last written at {stamp}, "
            f"over {job.recent_minutes} minutes ago",
        )
    if written.date() == now.date():
        return True, f"{job.name}: ran today, {path.name} written at {stamp}"
    return False, f"{job.name}: not today, {path.name} last written at {stamp}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    inst = sub.add_parser("install")
    inst.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    inst.add_argument("--only", default=None)
    inst.add_argument("--dry-run", action="store_true")
    chk = sub.add_parser("check-installed")
    chk.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ran = sub.add_parser("ran-today")
    ran.add_argument("name")
    sub.add_parser("today")
    args = parser.parse_args(argv)

    home = Path.home()
    uv = shutil.which("uv") or "/opt/homebrew/bin/uv"
    if args.command == "install":
        root = expand(args.root, home).resolve()
        for line in install(root, home, uv, args.only, args.dry_run):
            print(line)
        return 0
    if args.command == "check-installed":
        root = expand(args.root, home).resolve()
        problems = check_installed(root, home, uv)
        for p in problems:
            print(f"mac-jobs: {p}")
        if not problems:
            print(f"mac-jobs: all {len(JOBS)} jobs installed from {root} and loaded")
        return 1 if problems else 0
    if args.command == "ran-today":
        ok, line = ran_today(by_name(args.name), home)
        print(line)
        return 0 if ok else 1
    for job in JOBS:
        print(ran_today(job, home)[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
