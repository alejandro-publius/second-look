"""The Mac job that keeps /two's lab record: the key the Worker reads, the SQL, the refusals."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import pytest

from apps.api import fhir_routes
from scripts import cache_their_records as cache

ROOT = Path(__file__).resolve().parents[2]
TWO_TS = ROOT / "worker" / "src" / "two.ts"
LAB = {"resourceType": "Observation", "id": "lab-1", "note": [{"text": "it's 7.9 mg/L"}]}


def test_the_key_is_what_node_computes_for_the_same_query() -> None:
    if shutil.which("node") is None:
        pytest.skip("needs node")
    query = fhir_routes.theirs_query()
    script = (
        "const q = JSON.parse(process.argv[1]);"
        "const h = require('node:crypto').createHash('sha256')"
        ".update(JSON.stringify(q)).digest('hex').slice(0, 16);"
        "process.stdout.write('theirs-' + h);"
    )
    done = subprocess.run(
        ["node", "-e", script, json.dumps(query)], capture_output=True, text=True, check=True
    )
    assert cache.cache_key(query) == done.stdout


def test_the_worker_reads_the_same_query_and_the_same_key_expression() -> None:
    text = TWO_TS.read_text(encoding="utf-8")
    assert "theirs-${sha256Hex(JSON.stringify(theirsQuery(env))).slice(0, 16)}" in text
    q = fhir_routes.theirs_query()
    assert f'THEIRS_LOCATION = "{q["subject"]}"' in text
    assert f'THEIRS_CODE = "{q["code"].split("|")[1]}"' in text
    assert '_sort: "-date", _count: "1"' in text
    assert "fetch(" not in text, "the Worker must not fetch their sandbox itself"


def test_the_sql_round_trips_quotes_through_sqlite() -> None:
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE sandbox_cache (cache_key TEXT PRIMARY KEY, body TEXT NOT NULL,"
        " status TEXT NOT NULL, fetched_at TEXT NOT NULL)"
    )
    db.executescript(cache.insert_sql("theirs-abc", LAB, "2026-09-23T07:30:00Z"))
    body, status, when = db.execute(
        "SELECT body, status, fetched_at FROM sandbox_cache WHERE cache_key = 'theirs-abc'"
    ).fetchone()
    assert json.loads(body) == LAB
    assert (status, when) == ("ok", "2026-09-23T07:30:00Z")


def stub(monkeypatch: pytest.MonkeyPatch, observation: dict[str, Any] | None) -> list[str]:
    stored: list[str] = []
    monkeypatch.setattr(fhir_routes, "fetch_theirs_live", lambda: observation)
    monkeypatch.setattr(cache, "store", stored.append)
    monkeypatch.setattr(
        cache, "read_back", lambda _site: {"theirs_status": "cached", "theirs": observation}
    )
    return stored


def test_a_failed_fetch_stores_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = stub(monkeypatch, None)
    assert cache.main([]) == 1
    assert stored == []


def test_a_dry_run_prints_and_stores_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stored = stub(monkeypatch, LAB)
    assert cache.main(["--dry-run"]) == 0
    assert stored == []
    assert "INSERT OR REPLACE INTO sandbox_cache" in capsys.readouterr().out


def test_a_good_fetch_is_stored_and_read_back(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = stub(monkeypatch, LAB)
    assert cache.main([]) == 0
    assert len(stored) == 1 and cache.cache_key(fhir_routes.theirs_query()) in stored[0]


def test_it_refuses_the_host_hard_rule_9_names(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = stub(monkeypatch, LAB)
    monkeypatch.setenv("SANDBOX_BASE_URL", "https://api.enora-oah.eu/fhir")
    assert cache.main([]) == 2
    assert stored == []
