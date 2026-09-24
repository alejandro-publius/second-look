"""make demo-offline seeds its data with no network and no key (scripts/seed_demo.py)."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import seed_demo

ROOT = Path(__file__).resolve().parents[2]


def offline_env() -> dict[str, str]:
    """No key. No proxy either: the script's own guard is the wall under test here, and a proxy
    on this machine would let a lookup through it unseen."""
    drop = {*seed_demo.KEY_NAMES, "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"}
    return {k: v for k, v in os.environ.items() if k not in drop}


def test_the_seed_runs_offline_and_makes_a_creek_with_a_pipe_worth_testing(tmp_path: Path) -> None:
    out = tmp_path / "demo"
    audit = ROOT / "audit" / "log.jsonl"
    audit_before = audit.read_bytes() if audit.exists() else None
    done = subprocess.run(
        [sys.executable, "scripts/seed_demo.py", "--out", str(out)],
        cwd=ROOT,
        env=offline_env(),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    made = json.loads((out / "SEEDED.json").read_text(encoding="utf-8"))
    assert made["demo"] is True and made["network_attempts"] == 0
    assert len(made["visits"]) == 3 and made["city_visits"] == 3
    assert made["pipes_worth_testing"] == 1, "two people who passed reported the pipe"
    assert made["sittings_counted"] == 0, "every demo sitting is marked as a test"
    assert (out / "demo.db").exists()
    assert len(list((out / "fhir_store").rglob("visit-*.json"))) == 3
    assert (out / "audit.jsonl").exists(), "the audit line goes to the demo folder"
    after = audit.read_bytes() if audit.exists() else None
    assert after == audit_before, "the repository's audit log is never touched"


def test_the_guard_refuses_another_machine_and_allows_this_one() -> None:
    guard = seed_demo.NoNetwork()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    guard.install()
    try:
        with pytest.raises(seed_demo.NetworkRefused):
            socket.getaddrinfo("api.open-meteo.com", 443)
        with pytest.raises(seed_demo.NetworkRefused):
            socket.create_connection(("203.0.113.9", 443), timeout=1)
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(seed_demo.NetworkRefused):
                raw.connect(("203.0.113.9", 443))
        finally:
            raw.close()
        local = socket.create_connection(server.getsockname(), timeout=1)
        local.close()
    finally:
        guard.remove()
        server.close()
    assert guard.tried == [
        "lookup 'api.open-meteo.com'",
        "lookup '203.0.113.9'",
        "connect 203.0.113.9",
    ]


def test_it_will_not_empty_a_folder_it_did_not_make(tmp_path: Path) -> None:
    keep = tmp_path / "notes.txt"
    keep.write_text("mine", encoding="utf-8")
    assert seed_demo.main(["--out", str(tmp_path)]) == 2
    assert keep.read_text(encoding="utf-8") == "mine"
    assert seed_demo.main(["--out", str(ROOT)]) == 2
