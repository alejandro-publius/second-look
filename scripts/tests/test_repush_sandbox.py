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
    assert lines[0].startswith("visit-0001.json: 15 conditional creates")
    assert sum(1 for line in lines if line.startswith("  POST ")) == 15
    assert any("POST Practitioner if none exist Practitioner?identifier=" in line for line in lines)
    assert lines[-1] == (
        "dry run: 1 bundle(s), 15 resource(s), "
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
    assert len(rows) == 2 + 15
    new_rows = rows[2:]
    assert all(r["action"] == "create" for r in new_rows)
    assert {r["resourceType"] for r in new_rows} >= {"Location", "Observation", "Provenance"}
    assert new_rows[0]["id"] == "100"
    assert waits == [], "one bundle, no wait needed"
    assert lines[-1] == "pushed 1 bundle(s): 15 created, 0 already there"


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
    assert len(rows) == 30 and all(r["action"] == "exists" for r in rows)


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


# --bundle, --library and --evidence (Update 10 tier 2 item 1) ------------------------------------

REFERRAL = ROOT / "fhir" / "golden" / "referral-strawberry-creek-1.json"
EXAMPLE = ROOT / "fhir" / "golden" / "example-lab-result-strawberry-creek-1.json"
TRANSACTION = ROOT / "fhir" / "golden" / "visit-strawberry-creek-1.transaction.json"


def test_only_a_visit_bundle_can_be_named_with_bundle(tmp_path: Path) -> None:
    """A referral, an example result or a transaction file is refused by name, and skipped when
    it sits in the store, so nothing but a visit record ever reaches their sandbox."""
    assert len(rs.load_bundles(tmp_path, [GOLDEN])) == 1
    for wrong in (REFERRAL, EXAMPLE, TRANSACTION):
        with pytest.raises(rs.RepushError, match="not a visit Bundle"):
            rs.load_bundles(tmp_path, [wrong])
    folder = tmp_path / "mixed"
    folder.mkdir()
    for src in (GOLDEN, REFERRAL, EXAMPLE, TRANSACTION):
        shutil.copy(src, folder / src.name)
    assert [p.name for p, _ in rs.load_bundles(folder)] == [GOLDEN.name]


def library_response(tx: dict, status: str = "201 Created") -> dict:
    return {
        "resourceType": "Bundle",
        "type": "transaction-response",
        "entry": [{"response": {"status": status, "location": "Library/900/_history/1"}}],
    }


@respx.mock
def test_register_library_lists_the_ledgers_provenances_and_saves_the_evidence(
    ledger: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    with ledger.open("a") as f:
        f.write(
            json.dumps(
                {
                    "ts_utc": "t",
                    "action": "create",
                    "resourceType": "Provenance",
                    "id": "77",
                    "base": BASE,
                }
            )
            + "\n"
        )
        # A Provenance on some other server, and one we deleted, are not listed.
        f.write(
            json.dumps(
                {
                    "ts_utc": "t",
                    "action": "create",
                    "resourceType": "Provenance",
                    "id": "78",
                    "base": "https://elsewhere.test/fhir",
                }
            )
            + "\n"
        )
        f.write(
            json.dumps(
                {
                    "ts_utc": "t",
                    "action": "create",
                    "resourceType": "Provenance",
                    "id": "79",
                    "base": BASE,
                }
            )
            + "\n"
        )
        f.write(
            json.dumps(
                {
                    "ts_utc": "t",
                    "action": "delete",
                    "resourceType": "Provenance",
                    "id": "79",
                    "base": BASE,
                }
            )
            + "\n"
        )
    assert rs.created_provenances(BASE) == ["Provenance/77"]

    posted = respx.post(BASE).mock(return_value=httpx.Response(200, json=library_response({})))
    back = respx.get(f"{BASE}/Library/900").mock(
        return_value=httpx.Response(200, json={"resourceType": "Library", "id": "900"})
    )
    waits: list[float] = []
    lines: list[str] = []
    evidence = tmp_path / "docs" / "notes" / "sandbox_library.md"
    from datetime import date

    code = rs.register_library(
        BASE, today=date(2026, 9, 21), sleep=waits.append, out=lines.append, evidence=evidence
    )
    assert code == 0
    sent = json.loads(posted.calls.last.request.content)
    (entry,) = sent["entry"]
    assert entry["request"] == {
        "method": "POST",
        "url": "Library",
        "ifNoneExist": "Library?identifier=https://github.com/alejandro-publius/second-look/fhir/library-id|second-look-citizen-creek-checks",
    }
    library = entry["resource"]
    assert {
        "system": "https://github.com/alejandro-publius/second-look",
        "code": "second-look",
    } in library["meta"]["tag"]
    assert "id" not in library, "a conditional create lets the server pick the id"
    assert library["content"][-1]["url"] == "Provenance/77"
    assert library["extension"][1]["valueInteger"] == 1
    assert back.call_count == 1 and waits == [1.0], "read back after the one second gap"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert (
        rows[-1]["action"] == "create"
        and rows[-1]["resourceType"] == "Library"
        and rows[-1]["id"] == "900"
    )
    assert rows[-1]["bundle"] == "library:second-look-citizen-creek-checks"
    assert lines[-1] == "library: create Library/900, read back 200, 1 records"
    text = evidence.read_text()
    assert "Library: `Library/900` (create)" in text
    assert "docs/notes/sandbox-library.png" in text
    assert '"resourceType": "Library"' in text


@respx.mock
def test_main_mirrors_one_bundle_then_registers_the_library(
    ledger: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    monkeypatch.setattr(rs.time, "sleep", lambda _s: None)
    tx = rs.transactions(tmp_path, [GOLDEN])[0][1]
    calls: list[dict] = []

    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        if body["entry"][0]["request"]["url"] == "Library":
            return httpx.Response(200, json=library_response(body, "200 OK"))
        return httpx.Response(200, json=transaction_response(tx))

    respx.post(BASE).mock(side_effect=answer)
    respx.get(f"{BASE}/Library/900").mock(
        return_value=httpx.Response(200, json={"resourceType": "Library"})
    )
    code = rs.main(
        [
            "--bundle",
            str(GOLDEN),
            "--library",
            "--base-url",
            BASE,
            "--evidence",
            str(tmp_path / "e.md"),
        ]
    )
    assert code == 0
    assert (
        len(calls) == 2
        and len(calls[0]["entry"]) == 15
        and calls[1]["entry"][0]["request"]["url"] == "Library"
    )
    # The Library lists the Provenance the first transaction just created.
    assert calls[1]["entry"][0]["resource"]["content"][-1]["url"].startswith("Provenance/")
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert rows[-1] == {**rows[-1], "action": "exists", "resourceType": "Library", "id": "900"}


def test_library_alone_refuses_without_the_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SANDBOX_MIRROR_ENABLED", raising=False)
    assert rs.main(["--library"]) == 2


@respx.mock
def test_a_second_library_run_updates_the_entry_on_our_own_identifier(
    ledger: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Update 10C answer 3: the count follows each push. The first run created Library/900; the
    second run finds it in the ledger and does a conditional update by our identifier, which can
    only ever match our own resource. No search deletes anything."""
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    with ledger.open("a") as f:
        row = {
            "ts_utc": "t",
            "action": "create",
            "resourceType": "Library",
            "id": "900",
            "base": BASE,
        }
        f.write(json.dumps(row) + "\n")
    assert rs.library_on_server(BASE) == "900"
    put = respx.put(f"{BASE}/Library").mock(
        return_value=httpx.Response(200, json={"resourceType": "Library", "id": "900"})
    )
    respx.get(f"{BASE}/Library/900").mock(
        return_value=httpx.Response(200, json={"resourceType": "Library"})
    )
    lines: list[str] = []
    from datetime import date

    code = rs.register_library(
        BASE,
        today=date(2026, 9, 28),
        sleep=lambda _s: None,
        out=lines.append,
        refs=["Provenance/480", "Provenance/481"],
    )
    assert code == 0
    request = put.calls.last.request
    assert request.url.params["identifier"] == (
        "https://github.com/alejandro-publius/second-look/fhir/library-id|second-look-citizen-creek-checks"
    )
    sent = json.loads(request.content)
    assert sent["extension"][1]["valueInteger"] == 2, "the count is what this run put there"
    assert [c["url"] for c in sent["content"]][-2:] == ["Provenance/480", "Provenance/481"]
    tag = {"system": "https://github.com/alejandro-publius/second-look", "code": "second-look"}
    assert tag in sent["meta"]["tag"]
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert rows[-1]["action"] == "update" and rows[-1]["id"] == "900"
    assert lines[-1] == "library: update Library/900, read back 200, 2 records"
    # A Library we deleted is not updated; a fresh one would be created.
    with ledger.open("a") as f:
        row = {
            "ts_utc": "t",
            "action": "delete",
            "resourceType": "Library",
            "id": "900",
            "base": BASE,
        }
        f.write(json.dumps(row) + "\n")
    assert rs.library_on_server(BASE) is None


@respx.mock
def test_push_hands_its_provenances_to_the_library(
    ledger: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SANDBOX_MIRROR_ENABLED", "true")
    tx = rs.transactions(tmp_path, [GOLDEN])[0][1]
    respx.post(BASE).mock(return_value=httpx.Response(200, json=transaction_response(tx, "200 OK")))
    seen: list[str] = []
    code = rs.push(
        tmp_path, BASE, sleep=lambda _s: None, out=lambda _l: None, only=[GOLDEN], provenances=seen
    )
    assert code == 0
    assert len(seen) == 1 and seen[0].startswith("Provenance/"), "one Provenance per visit"


def test_a_demo_walk_record_is_never_mirrored() -> None:
    from datetime import UTC, datetime

    from core.walks import walk_bundle

    walk = {"id": "v03", "spot_name": "The stretch in the clip", "creek_name": "A creek"}
    bundle = walk_bundle(walk, {"bank_type": "present"}, datetime(2026, 9, 24, 16, 0, tzinfo=UTC))
    assert rs._is_visit_bundle(bundle) is False
    untagged = {**bundle, "meta": {}}
    assert rs._is_visit_bundle(untagged) is True
