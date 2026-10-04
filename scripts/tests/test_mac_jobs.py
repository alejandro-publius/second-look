"""scripts/mac_jobs.py: every launchd job in one table, its installer, and the MAC_JOBS doc.

The installer runs for real with HOME in a temporary folder and stand-ins for launchctl and
plutil on PATH, so nothing is loaded on this machine and nothing under ~/Library is touched.
"""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from evals import wave2_analysis
from scripts import lock_analysis, mac_jobs

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "internal" / "MAC_JOBS.md"


def stand_ins(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("launchctl", "plutil"):
        (bin_dir / name).write_text(f'#!/bin/sh\necho "{name} $*" >> "{tmp_path}/calls.log"\n')
        (bin_dir / name).chmod(0o755)
    (bin_dir / "uv").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "uv").chmod(0o755)
    return {**os.environ, "HOME": str(tmp_path), "PATH": f"{bin_dir}:/usr/bin:/bin"}


def install(
    tmp_path: Path, *args: str, tz: str = "America/Los_Angeles"
) -> subprocess.CompletedProcess[str]:
    env = {**stand_ins(tmp_path), "TZ": tz}
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mac_jobs.py"), "install", *args],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_every_job_runs_a_script_that_exists_and_has_a_distinct_label() -> None:
    labels = [j.label for j in mac_jobs.JOBS]
    assert len(labels) == len(set(labels)) == 9
    for job in mac_jobs.JOBS:
        assert (ROOT / job.script()).is_file(), job.script()
        assert (job.calendar is None) != (job.interval is None)


def test_the_lock_job_fires_at_18_10_on_sep_27_in_california() -> None:
    assert mac_jobs.lock_calendar(ZoneInfo("America/Los_Angeles")) == {
        "Month": 9, "Day": 27, "Hour": 18, "Minute": 10,
    }  # fmt: skip
    assert mac_jobs.lock_calendar(ZoneInfo("UTC")) == {
        "Month": 9,
        "Day": 28,
        "Hour": 1,
        "Minute": 10,
    }
    assert mac_jobs.LOCK_JOB_UTC > lock_analysis.DATA_LOCK_UTC


def test_the_second_run_fires_at_21_10_on_oct_2_in_california() -> None:
    when = mac_jobs.LOCK2_JOB_UTC
    assert when == datetime(2026, 10, 3, 4, 10, tzinfo=UTC) == wave2_analysis.LOCK_JOB_UTC
    assert when - wave2_analysis.SECOND_LOCK_UTC == timedelta(minutes=10)
    assert lock_analysis.SECOND.lock_utc == wave2_analysis.SECOND_LOCK_UTC
    job = {j.name: j for j in mac_jobs.jobs(ZoneInfo("America/Los_Angeles"))}["lock2"]
    assert job.calendar == {"Month": 10, "Day": 2, "Hour": 21, "Minute": 10}
    assert mac_jobs.lock_calendar(ZoneInfo("UTC"), when) == {
        "Month": 10,
        "Day": 3,
        "Hour": 4,
        "Minute": 10,
    }
    assert job.command == ("uv", "run", "python", "scripts/lock_analysis.py", "--wave", "2")
    assert "2026-10-03T04:10:00Z" in job.when and "Oct 2, 21:10 PDT" in job.when
    # The first run is as it was: the same script, no option, its own time.
    first = mac_jobs.by_name("lock")
    assert first.command == ("uv", "run", "python", "scripts/lock_analysis.py")
    assert first.options() == () and job.options() == ("--wave", "2")
    # DEPLOY.md lists every job; the second run's row gives the same instant and its targets.
    deploy = (ROOT / "DEPLOY.md").read_text(encoding="utf-8")
    (row,) = [ln for ln in deploy.splitlines() if ln.startswith("| `com.secondlook.lock2` |")]
    assert "2026-10-03T04:10:00Z" in row and "21:10 on Oct 2" in row
    assert "`scripts/lock_analysis.py --wave 2`" in row and "`make lock-analysis-2-install`" in row


def test_install_writes_and_loads_every_job_from_the_checkout(tmp_path: Path) -> None:
    proc = install(tmp_path, "--root", str(ROOT))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    agents = tmp_path / "Library" / "LaunchAgents"
    plists = {p.stem: plistlib.loads(p.read_bytes()) for p in agents.glob("*.plist")}
    assert set(plists) == {j.label for j in mac_jobs.JOBS}
    for label, doc in plists.items():
        assert doc["WorkingDirectory"] == str(ROOT)
        assert doc["StandardOutPath"].startswith(f"{tmp_path}/second-look-backups/")
        scripts = [
            a for a in doc["ProgramArguments"] if "/scripts/" in a and a.endswith((".py", ".sh"))
        ]
        assert all(Path(s).is_file() for s in scripts), label
    lock = plists["com.secondlook.lock"]
    assert lock["StartCalendarInterval"] == {"Month": 9, "Day": 27, "Hour": 18, "Minute": 10}
    assert lock["ProgramArguments"][-1] == f"{ROOT}/scripts/lock_analysis.py"
    second = plists["com.secondlook.lock2"]
    assert second["StartCalendarInterval"] == {"Month": 10, "Day": 2, "Hour": 21, "Minute": 10}
    assert second["ProgramArguments"][-3:] == [f"{ROOT}/scripts/lock_analysis.py", "--wave", "2"]
    assert second["ProgramArguments"][1:3] == ["run", "python"]
    assert second["StandardOutPath"].endswith("/second-look-backups/logs/lock2.out")
    assert plists["com.secondlook.uptime"]["StartInterval"] == 600
    assert plists["com.secondlook.repush"]["ProgramArguments"][-1].endswith(
        "scripts/sandbox_retry.py"
    )
    calls = (tmp_path / "calls.log").read_text()
    assert calls.count("launchctl bootstrap") == 9 and calls.count("plutil -lint") == 9


def test_install_only_the_lock(tmp_path: Path) -> None:
    proc = install(tmp_path, "--root", str(ROOT), "--only", "lock", tz="UTC")
    assert proc.returncode == 0, proc.stderr
    plists = list((tmp_path / "Library" / "LaunchAgents").glob("*.plist"))
    assert [p.name for p in plists] == ["com.secondlook.lock.plist"]
    doc = plistlib.loads(plists[0].read_bytes())
    assert doc["StartCalendarInterval"] == {"Month": 9, "Day": 28, "Hour": 1, "Minute": 10}


def test_install_only_the_second_run(tmp_path: Path) -> None:
    proc = install(tmp_path, "--root", str(ROOT), "--only", "lock2", tz="UTC")
    assert proc.returncode == 0, proc.stderr
    plists = list((tmp_path / "Library" / "LaunchAgents").glob("*.plist"))
    assert [p.name for p in plists] == ["com.secondlook.lock2.plist"]
    doc = plistlib.loads(plists[0].read_bytes())
    assert doc["StartCalendarInterval"] == {"Month": 10, "Day": 3, "Hour": 4, "Minute": 10}
    assert doc["ProgramArguments"][-2:] == ["--wave", "2"]
    assert (tmp_path / "calls.log").read_text().count("launchctl bootstrap") == 1


def test_install_refuses_a_checkout_that_lacks_the_new_scripts(tmp_path: Path) -> None:
    old = tmp_path / "old-checkout"
    (old / "scripts").mkdir(parents=True)
    (old / "scripts" / "backup_d1.sh").write_text("")
    proc = install(tmp_path, "--root", str(old))
    assert proc.returncode != 0
    assert "fast-forward it to origin/depth first" in proc.stdout + proc.stderr
    assert not (tmp_path / "Library").exists()


@pytest.mark.parametrize(
    ("installer", "name"),
    [
        ("install_anchor_job.sh", "anchor"),
        ("install_cache_job.sh", "theirs"),
        ("install_inaturalist_job.sh", "inaturalist"),
        ("install_repush_job.sh", "repush"),
        ("install_backup_job.sh", "backup"),
    ],
)
def test_the_one_job_installers_agree_with_the_table(
    tmp_path: Path, installer: str, name: str
) -> None:
    env = stand_ins(tmp_path)
    proc = subprocess.run(
        ["bash", str(ROOT / "scripts" / installer)], env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    job = mac_jobs.by_name(name)
    theirs = plistlib.loads(
        (tmp_path / "Library" / "LaunchAgents" / f"{job.label}.plist").read_bytes()
    )
    ours = mac_jobs.plist(job, ROOT, tmp_path, str(tmp_path / "bin" / "uv"))
    for key in (
        "Label",
        "ProgramArguments",
        "WorkingDirectory",
        "StartCalendarInterval",
        "StandardOutPath",
        "StandardErrorPath",
    ):
        assert theirs[key] == ours[key], f"{installer}: {key}"


def test_ran_today_reads_the_log_date_and_uptime_reads_the_last_minutes(tmp_path: Path) -> None:
    logs = tmp_path / "second-look-backups" / "logs"
    logs.mkdir(parents=True)
    anchor = mac_jobs.by_name("anchor")
    ok, line = mac_jobs.ran_today(anchor, tmp_path)
    assert not ok and "does not exist yet" in line
    (logs / "anchor.log").write_text("x\n")
    assert mac_jobs.ran_today(anchor, tmp_path)[0]
    yesterday = (datetime.now() - timedelta(days=1)).timestamp()
    os.utime(logs / "anchor.log", (yesterday, yesterday))
    assert not mac_jobs.ran_today(anchor, tmp_path)[0]
    up = mac_jobs.by_name("uptime")
    (logs / "uptime.out").write_text("x\n")
    assert mac_jobs.ran_today(up, tmp_path)[0]
    half_hour = (datetime.now() - timedelta(minutes=30)).timestamp()
    os.utime(logs / "uptime.out", (half_hour, half_hour))
    assert not mac_jobs.ran_today(up, tmp_path)[0]


def test_a_one_shot_job_ran_if_its_log_was_written_on_its_day_or_after(tmp_path: Path) -> None:
    # Asked on the morning after, the second lock's job ran the evening before.
    (tmp_path / "second-look-backups").mkdir(parents=True)
    log = tmp_path / "second-look-backups" / "lock.log"
    log.write_text("x\n")
    lock2 = mac_jobs.by_name("lock2")
    assert lock2.calendar is not None
    year, month, day = datetime.now().year, lock2.calendar["Month"], lock2.calendar["Day"]
    evening = datetime(year, month, day, 21, 41).astimezone()
    os.utime(log, (evening.timestamp(), evening.timestamp()))
    morning_after = datetime(year, month, day, 8, 0).astimezone() + timedelta(days=1)
    ok, line = mac_jobs.ran_today(lock2, tmp_path, now=morning_after)
    assert ok and f"ran on {evening.date()}" in line
    before = datetime(year, month, day, 21, 41).astimezone() - timedelta(days=1)
    os.utime(log, (before.timestamp(), before.timestamp()))
    ok, line = mac_jobs.ran_today(lock2, tmp_path, now=morning_after)
    assert not ok and "not since its day" in line


def test_the_lock_job_leaves_exactly_the_files_the_other_jobs_write() -> None:
    assert set(mac_jobs.mac_job_files()) == {
        "proofs/",
        "results/ots.json",
        "fhir/sandbox_ledger.jsonl",
    }
    assert lock_analysis.allowed("proofs/audit-head-2026-09-28.ots", mac_jobs.mac_job_files())
    assert not lock_analysis.allowed("README.md", mac_jobs.mac_job_files())
    assert not lock_analysis.allowed("results/ots.json.bak", mac_jobs.mac_job_files())
    # The audit log is not set aside like those. Lines the re-push job added to it are carried.
    assert not lock_analysis.allowed("audit/log.jsonl", mac_jobs.mac_job_files())


def test_the_lines_the_second_run_carries_are_of_the_kind_the_re_push_job_writes() -> None:
    assert mac_jobs.mac_job_audit_kinds() == ("sandbox_push",)
    assert mac_jobs.by_name("repush").audit_kinds == ("sandbox_push",)
    writer = (ROOT / "scripts" / "repush_sandbox.py").read_text(encoding="utf-8")
    assert '"sandbox_push", payload' in writer
    assert lock_analysis.SECOND.carries_audit_lines and not lock_analysis.FIRST.carries_audit_lines


@pytest.mark.skipif(
    not DOC.parent.is_dir(), reason="the team's working notes is removed when the repository goes public"
)
def test_mac_jobs_md_lists_every_job_with_its_time_log_and_ran_today_command() -> None:
    text = DOC.read_text(encoding="utf-8")
    rows = {
        m.group(1): m.group(0)
        for m in re.finditer(r"^\| `(com\.secondlook\.\w+)` \|.*$", text, re.M)
    }
    assert set(rows) == {j.label for j in mac_jobs.JOBS}
    for job in mac_jobs.JOBS:
        row = rows[job.label]
        assert job.when in row, f"{job.label}: the time is not {job.when!r}"
        assert job.script() in row
        assert f"~/second-look-backups/{job.ran_file()}" in row
        assert f"`uv run python scripts/mac_jobs.py ran-today {job.name}`" in row
    assert "make mac-jobs-install" in text and "~/second-look-depth" in text
    # The table is the one the script writes, row for row and word for word.
    assert mac_jobs.doc_with_table(text) == text
    assert mac_jobs.doc_table().count("\n") == len(mac_jobs.JOBS) + 2
    assert "`scripts/lock_analysis.py --wave 2`" in rows["com.secondlook.lock2"]
    assert "make lock-analysis-2-install" in text and "make lock-analysis-2-ready" in text


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS only")
def test_each_plist_passes_plutil(tmp_path: Path) -> None:
    for job in mac_jobs.JOBS:
        path = tmp_path / f"{job.label}.plist"
        path.write_bytes(
            plistlib.dumps(mac_jobs.plist(job, ROOT, tmp_path, "/opt/homebrew/bin/uv"))
        )
        assert subprocess.run(["plutil", "-lint", str(path)], capture_output=True).returncode == 0
