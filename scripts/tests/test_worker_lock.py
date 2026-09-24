"""The Worker's data lock is the Python lock, and its test clock never reaches a deployed Worker.

The live site's API is the Worker, so judge mode opens at the time worker/src/index.ts holds, not
the time core/lock.py holds. Only a test that reads both keeps them the same (review REVIEW_03 R52,
REVIEW_02 F60). The Worker reads E2E_NOW, a fixed time for its lock, so worker/test/e2e.mjs can run
both sides of the lock on every run; a deployed Worker must never be given it.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from core.lock import DATA_LOCK_UTC

ROOT = Path(__file__).resolve().parents[2]
WORKER_INDEX = ROOT / "worker" / "src" / "index.ts"
LOCK_RE = re.compile(r'^const DATA_LOCK_UTC = Date\.parse\("([^"]+)"\);$', re.M)


def worker_lock() -> datetime:
    found = LOCK_RE.findall(WORKER_INDEX.read_text(encoding="utf-8"))
    assert len(found) == 1, "worker/src/index.ts holds one DATA_LOCK_UTC"
    return datetime.fromisoformat(found[0].replace("Z", "+00:00"))


def test_the_worker_lock_is_the_python_lock() -> None:
    assert worker_lock() == DATA_LOCK_UTC


def test_no_deployed_config_sets_the_test_clock() -> None:
    deployed = [
        ROOT / "worker" / "wrangler.jsonc",
        ROOT / "apps" / "web" / "wrangler.jsonc",
        ROOT / "scripts" / "deploy.sh",
        ROOT / "DEPLOY.md",
    ]
    deployed += sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    for path in deployed:
        if path.exists():
            assert "E2E_NOW" not in path.read_text(encoding="utf-8"), path.relative_to(ROOT)


def test_only_the_e2e_run_sets_the_test_clock() -> None:
    setters = []
    kinds = {".ts", ".mjs", ".js", ".json", ".jsonc", ".sh"}
    for path in sorted((ROOT / "worker").rglob("*")):
        if not path.is_file() or path.suffix not in kinds:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(("worker/node_modules/", "worker/.wrangler/", "worker/dist/")):
            continue
        if "E2E_NOW" in path.read_text(encoding="utf-8", errors="replace"):
            setters.append(rel)
    assert setters == ["worker/src/index.ts", "worker/test/e2e.mjs"]
