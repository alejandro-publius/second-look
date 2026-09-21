"""repush_sandbox: dry run without network, guarded pushes, ledger-only deletes. All HTTP mocked."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import httpx
import pytest
import respx

from scripts import repush_sandbox as rs

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "fhir" / "golden" / "visit-strawberry-creek-1.json"
BASE = "https://sandbox.test/fhir"


@pytest.fixture
def store(tmp_path: Path) -> Path:
    folder = tmp_path / "fhir_store"
    folder.mkdir()
    shutil.copy(GOLDEN, folder / "visit-0001.json")
    (folder / "index.json").write_text('{"spots": {}, "latest": "visit-0001"}')
    return folder


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "ledger.jsonl"
    path.write_text(
        '{"ts_utc":"2026-09-20T21:37:20Z","action":"create","resourceType":"Location","id":"451"}\n'
        '{"ts_utc":"2026-09-20T21:37:21Z","action":"delete","resourceType":"Location","id":"451","status":"200"}\n'
    )
    monkeypatch.setattr(rs, "LEDGER", path)
    return path


def transaction_response(tx: dict, status: str = "201 Created") -> dict:
    entries = []
    for i, entry in enumerate(tx["entry"]):
        rtype = entry["request"]["url"]
        entries.append(
            {"response": {"status": status, "location": f"{rtype}/{100 + i}/_history/1"}}
        )
    return {"resourceType": "Bundle", "type": "transaction-response", "entry": entries}


@respx.mock
def test_dry_run_prints_the_plan_and_makes_no_network_call(store: Path) -> None:
    lines: list[str] = []
    assert rs.main(["--dry-run", "--store", str(store)]) == 0
    assert rs.dry_run(store, lines.append) == 0
    assert lines[0].startswith("visit-0001.json: 14 conditional creates")
    assert sum(1 for line in lines if line.startswith("  POST ")) == 14
    assert any("POST Practitioner if none exist Practitioner?identifier=" in line for line in lines)
    assert lines[-1] == (
        "dry run: 1 bundle(s), 14 resource(s), "
        "tag https://github.com/alejandro-publius/second-look|second-look, no network"
    )
    assert respx.calls.call_count == 0


def test_dry_run_on_an_empty_store(tmp_path: Path) -> None:
    lines: list[str] = []
    assert rs.dry_run(tmp_path / "missing", lines.append) == 0
    assert lines == [
        "dry run: 0 bundle(s), 0 resource(s), "
        "tag https://github.com/alejandro-publius/second-look|second-look, no network"
    ]


def test_index_file_is_not_a_bundle(store: Path) -> None:
    assert [p.name for p, _ in rs.load_bundles(store)] == ["visit-0001.json"]


def test_push_refuses_without_the_flag(store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SANDBOX_MIRROR_ENABLED", raising=False)
    assert rs.main(["--store", str(store), "--base-url", BASE]) == 2
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "false")
    assert rs.main(["--store", str(store), "--base-url", BASE]) == 2


def test_push_refuses_the_forbidden_host(store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    assert rs.main(["--store", str(store), "--base-url", "https://api.enora-oah.eu/fhir"]) == 2


@respx.mock
def test_push_posts_a_tagged_transaction_and_records_created_ids(
    store: Path, ledger: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    tx = rs.transactions(store)[0][1]
    route = respx.post(BASE).mock(return_value=httpx.Response(200, json=transaction_response(tx)))
    waits: list[float] = []
    lines: list[str] = []
    assert rs.push(store, BASE, sleep=waits.append, out=lines.append) == 0
    assert route.call_count == 1
    request = route.calls.last.request
    assert (
        request.headers["User-Agent"]
        == "second-look (+https://github.com/alejandro-publius/second-look)"
    )
    assert request.headers["Content-Type"] == "application/fhir+json"
    sent = json.loads(request.content)
    assert sent["type"] == "transaction"
    for entry in sent["entry"]:
        assert entry["request"]["method"] == "POST"
        assert "ifNoneExist" in entry["request"]
        assert {
            "system": "https://github.com/alejandro-publius/second-look",
            "code": "second-look",
        } in entry["resource"]["meta"]["tag"]
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert len(rows) == 2 + 14
    new_rows = rows[2:]
    assert all(r["action"] == "create" for r in new_rows)
    assert {r["resourceType"] for r in new_rows} >= {"Location", "Observation", "Provenance"}
    assert new_rows[0]["id"] == "100"
    assert waits == [], "one bundle, no wait needed"
    assert lines[-1] == "pushed 1 bundle(s): 14 created, 0 already there"


@respx.mock
def test_push_waits_one_second_between_bundles_and_records_matches(
    store: Path, ledger: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    shutil.copy(store / "visit-0001.json", store / "visit-0002.json")
    tx = rs.transactions(store)[0][1]
    respx.post(BASE).mock(return_value=httpx.Response(200, json=transaction_response(tx, "200 OK")))
    waits: list[float] = []
    assert rs.push(store, BASE, sleep=waits.append, out=lambda _: None) == 0
    assert waits == [1.0]
    rows = [json.loads(line) for line in ledger.read_text().splitlines()][2:]
    assert len(rows) == 28 and all(r["action"] == "exists" for r in rows)


@respx.mock
def test_push_stops_on_a_server_error_and_writes_nothing(
    store: Path, ledger: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    respx.post(BASE).mock(return_value=httpx.Response(500, text="boom"))
    assert rs.push(store, BASE, sleep=lambda _: None, out=lambda _: None) == 1
    assert len(ledger.read_text().splitlines()) == 2


@respx.mock
def test_delete_only_an_id_from_the_ledger(ledger: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    row = {"ts_utc": "2026-09-21T00:00:00Z", "action": "create", "resourceType": "Observation"}
    ledger.write_text(ledger.read_text() + json.dumps(row | {"id": "777"}) + "\n")
    route = respx.delete(f"{BASE}/Observation/777").mock(return_value=httpx.Response(200))
    assert rs.main(["--delete-ledger-id", "777", "--base-url", BASE]) == 0
    assert route.call_count == 1
    last = json.loads(ledger.read_text().splitlines()[-1])
    assert last == {
        "ts_utc": last["ts_utc"],
        "action": "delete",
        "resourceType": "Observation",
        "id": "777",
        "status": "200",
        "base": BASE,
    }
    # a second delete of the same id is refused without a request
    assert rs.main(["--delete-ledger-id", "777", "--base-url", BASE]) == 2
    assert route.call_count == 1


@respx.mock
def test_refused_delete_is_recorded_and_can_be_retried(
    ledger: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    row = {"ts_utc": "2026-09-21T00:00:00Z", "action": "create", "resourceType": "Location"}
    ledger.write_text(ledger.read_text() + json.dumps(row | {"id": "1002"}) + "\n")
    route = respx.delete(f"{BASE}/Location/1002").mock(return_value=httpx.Response(409))
    assert rs.main(["--delete-ledger-id", "1002", "--base-url", BASE]) == 1
    last = json.loads(ledger.read_text().splitlines()[-1])
    assert last["action"] == "delete_failed" and last["status"] == "409"
    route.mock(return_value=httpx.Response(204))
    assert rs.main(["--delete-ledger-id", "1002", "--base-url", BASE]) == 0
    assert json.loads(ledger.read_text().splitlines()[-1])["action"] == "delete"
    assert route.call_count == 2


@respx.mock
def test_delete_refuses_unknown_ids_searches_and_operations(
    ledger: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    assert rs.main(["--delete-ledger-id", "999", "--base-url", BASE]) == 2
    assert rs.main(["--delete-ledger-id", "451", "--base-url", BASE]) == 2, "already deleted"
    assert rs.main(["--delete-ledger-id", "Location?_tag=x", "--base-url", BASE]) == 2
    assert rs.main(["--delete-ledger-id", "$expunge", "--base-url", BASE]) == 2
    assert respx.calls.call_count == 0


def test_parse_location() -> None:
    assert rs._parse_location("Observation/12/_history/1") == ("Observation", "12")
    assert rs._parse_location("https://x/fhir/Location/451") == ("Location", "451")
    assert rs._parse_location("") is None
