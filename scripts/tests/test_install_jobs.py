"""The launchd installers: what each daily job runs, when, and from where.

Each installer runs for real with HOME in a temporary folder and stand-ins for launchctl and uv,
so nothing is loaded on this machine. The plist it writes is read with plistlib, which runs on
any system. Only `plutil -lint`, which install_anchor_job.sh runs on what it wrote, needs macOS:
without it a stand-in takes its place, so on the Linux CI runner every test here still runs and
only the lint case is skipped (REVIEW_03 R54).
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
LINTS = [
    pytest.param(
        "real",
        marks=pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS only"),
    ),
    "stand-in",
]


def install(tmp_path: Path, script: str, lint: str) -> tuple[dict[str, Any], Path]:
    """Run an installer; the plist it wrote, and the folder where each stand-in logged its calls."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name in ("launchctl", *(("plutil",) if lint == "stand-in" else ())):
        (fake_bin / name).write_text(f'#!/bin/sh\necho "$@" >> "{tmp_path / name}.calls"\n')
    (fake_bin / "uv").write_text("#!/bin/sh\nexit 0\n")
    for f in fake_bin.iterdir():
        f.chmod(0o755)
    env = {**os.environ, "HOME": str(tmp_path), "PATH": f"{fake_bin}:/usr/bin:/bin"}
    proc = subprocess.run(
        ["bash", str(ROOT / "scripts" / script)], env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    plists = list((tmp_path / "Library" / "LaunchAgents").glob("*.plist"))
    assert len(plists) == 1, plists
    return plistlib.loads(plists[0].read_bytes()), tmp_path


@pytest.mark.parametrize("lint", LINTS)
def test_the_anchor_job_runs_the_anchor_then_the_status_daily(tmp_path: Path, lint: str) -> None:
    job, logs = install(tmp_path, "install_anchor_job.sh", lint)
    assert job["Label"] == "com.secondlook.anchor"
    assert job["ProgramArguments"][:2] == ["/bin/bash", "-c"]
    command = job["ProgramArguments"][-1]
    assert command.index("anchor_audit_head.py") < command.index("ots_status.py")
    assert job["StartCalendarInterval"] == {"Hour": 6, "Minute": 0}
    assert job["WorkingDirectory"] == str(ROOT)
    assert "bootstrap" in (logs / "launchctl.calls").read_text()
    if lint == "stand-in":
        assert (logs / "plutil.calls").read_text().startswith("-lint ")


@pytest.mark.parametrize("lint", LINTS)
def test_the_inaturalist_job_runs_the_cache_daily(tmp_path: Path, lint: str) -> None:
    job, logs = install(tmp_path, "install_inaturalist_job.sh", lint)
    assert job["Label"] == "com.secondlook.inaturalist"
    uv = str(tmp_path / "bin" / "uv")
    script = f"{ROOT}/scripts/cache_inaturalist.py"
    assert job["ProgramArguments"] == [uv, "run", "python", script]
    assert (ROOT / "scripts" / "cache_inaturalist.py").is_file()
    assert job["StartCalendarInterval"] == {"Hour": 7, "Minute": 45}
    assert job["WorkingDirectory"] == str(ROOT)
    assert "bootstrap" in (logs / "launchctl.calls").read_text()
