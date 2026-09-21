"""Contract tests for the MCP server: five tools, every answer with its resource ids, both
sources, and one real run over stdio.

The records come from the real API and the real store: two people who passed report a pipe at
the Faculty Glade pin, one quiet visit sits three reaches below in the park. The export is then
what scripts/export_records.py writes, and the API source reads the same app over HTTP."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from mcp.types import TextContent
from sqlmodel import Session

from apps.api import core_calls
from apps.api.db import engine
from apps.api.tests.conftest import freeze_now
from apps.api.tests.test_city import (
    GOOD_ANSWERS,
    NOW,
    PARK_PIN,
    QUIET_ANSWERS,
    SOUTH_FORK_PIN,
    _dry,
    a_visit,
    passing_session,
)
from apps.mcp.server import build_server
from apps.mcp.source import ApiSource, ExportSource, SourceError
from scripts.export_records import export

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ["list_creeks", "get_creek_record", "list_findings", "get_observer_score", "explain_number"]


@pytest.fixture
def records(client, monkeypatch, tmp_path: Path) -> dict[str, Any]:
    """Two pipe reports by people who passed, one quiet visit downstream, exported."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    first = a_visit(
        client, token=passing_session(client), spot=SOUTH_FORK_PIN, answers=GOOD_ANSWERS
    )
    second = a_visit(
        client,
        token=passing_session(client),
        spot={"spot_id": first["spot_id"]},
        answers=GOOD_ANSWERS,
    )
    quiet = a_visit(client, token=None, spot=PARK_PIN, answers=QUIET_ANSWERS)
    out = tmp_path / "export"
    with Session(engine) as db:
        counts = export(db, out, now=datetime(2026, 9, 25, 15, 0, tzinfo=UTC))
    assert counts == {"creeks": 1, "spots": 2, "bundles": 3}
    return {
        "client": client,
        "out": out,
        "visits": [first, second, quiet],
        "spot": first["spot_id"],
    }


def text_of(result: Any) -> str:
    part = result.content[0]
    assert isinstance(part, TextContent), part
    return part.text


def payload(result: Any) -> dict[str, Any]:
    if result.structured_content:
        data = result.structured_content
        return data["result"] if set(data) == {"result"} else data
    return json.loads(text_of(result))


async def call(server: Any, name: str, **arguments: Any) -> dict[str, Any]:
    async with Client(server) as mcp_client:
        result = await mcp_client.call_tool(name, arguments)
    assert not result.is_error, result.content
    return payload(result)


async def call_error(server: Any, name: str, **arguments: Any) -> str:
    async with Client(server) as mcp_client:
        result = await mcp_client.call_tool(name, arguments)
    assert result.is_error, "expected a plain error"
    return text_of(result)


async def test_the_five_tools_each_say_what_they_do(records: dict[str, Any]) -> None:
    server = build_server(ExportSource(records["out"]))
    async with Client(server) as mcp_client:
        tools = (await mcp_client.list_tools()).tools
    assert sorted(t.name for t in tools) == sorted(TOOLS)
    for tool in tools:
        assert tool.description and len(tool.description) > 40, tool.name
    schema = {t.name: t.input_schema for t in tools}
    assert set(schema["list_findings"]["properties"]) == {
        "creek",
        "feature",
        "min_observers",
        "passed_only",
    }
    assert schema["explain_number"]["required"] == ["creek", "path"]


async def test_every_answer_carries_the_ids_behind_it(records: dict[str, Any]) -> None:
    server = build_server(ExportSource(records["out"]))
    visit_ids = {v["visit_id"] for v in records["visits"]}
    creeks = await call(server, "list_creeks")
    assert [c["creek"] for c in creeks["creeks"]] == ["strawberry-creek"]
    assert set(creeks["fhir"]) == {f"/api/fhir/Bundle/{v}" for v in visit_ids}
    assert set(creeks["resource_ids"]) == {f"Bundle/{v}" for v in visit_ids}

    record = await call(server, "get_creek_record", creek="strawberry-creek")
    assert record["visits"] == 3 and set(record["visit_ids"]) == visit_ids
    assert record["creek_slug"] == "strawberry-creek"
    (pipe,) = record["pipes_worth_testing"]
    assert pipe["observers"] == 2 and pipe["referral"].startswith("/api/fhir/referral/")
    assert record["downstream_notes"], "the glade finding puts lines on the reaches below"
    for section in ("findings", "pipes_worth_testing", "downstream_notes"):
        for item in record[section]:
            assert item["visit_ids"] and item["fhir"], f"{section} item without evidence"
    assert set(record["resource_ids"]) == {f"Bundle/{v}" for v in visit_ids}


async def test_list_findings_filters_by_feature_people_and_passing(records: dict[str, Any]) -> None:
    server = build_server(ExportSource(records["out"]))
    everything = await call(server, "list_findings")
    features = {f["feature"] for f in everything["findings"]}
    assert {"artificial_bank", "pipe_running"} <= features
    assert all(f["resource_ids"] for f in everything["findings"])

    pipes = await call(server, "list_findings", feature="pipe_running", min_observers=2)
    (pipe,) = pipes["findings"]
    assert pipe["observers"] == 2 and pipe["passed_observers"] == 2
    assert pipe["creek"] == "strawberry-creek" and pipe["creek_name"] == "Strawberry Creek"
    assert set(pipe["resource_ids"]) == {f"Bundle/{v['visit_id']}" for v in records["visits"][:2]}

    # Both people passed every feature, so passed_only changes nothing here; asking for three
    # people finds nothing, and the answer still says what was asked.
    passed = await call(
        server, "list_findings", feature="pipe_running", min_observers=2, passed_only=True
    )
    assert len(passed["findings"]) == 1
    none = await call(server, "list_findings", min_observers=3)
    assert none["findings"] == [] and none["resource_ids"] == []
    assert none["filters"] == {
        "creek": None,
        "feature": None,
        "min_observers": 3,
        "passed_only": False,
    }
    assert "at least 1" in await call_error(server, "list_findings", min_observers=0)


async def test_get_observer_score_by_visit_and_by_practitioner(records: dict[str, Any]) -> None:
    server = build_server(ExportSource(records["out"]))
    first = records["visits"][0]["visit_id"]
    by_visit = await call(server, "get_observer_score", observer=first)
    assert by_visit["practitioner_id"].startswith("sl-practitioner-")
    assert by_visit["tested_on"] == "2026-09-25" and by_visit["score_counts_until"] == "2026-12-24"
    assert {s["feature"]: s["correct"] for s in by_visit["scores"]} == {
        "artificial_bank": 4,
        "dug_out_channel": 4,
        "invasive_plant": 4,
        "pipe_running": 4,
    }
    assert by_visit["resource_ids"] == [f"Bundle/{first}"]

    by_person = await call(
        server, "get_observer_score", observer=f"Practitioner/{by_visit['practitioner_id']}"
    )
    assert by_person["practitioner_id"] == by_visit["practitioner_id"]
    assert by_person["from_visit"] == first

    # The quiet visit was anonymous: a qualification less Practitioner, no scores, and it says so.
    quiet = await call(server, "get_observer_score", observer=records["visits"][2]["visit_id"])
    assert quiet["scores"] == [] and "no per feature score" in quiet["scores_note"]
    assert "no record names" in await call_error(
        server, "get_observer_score", observer="sl-practitioner-nobody0000"
    )


async def test_explain_number_gives_the_ids_behind_a_figure(records: dict[str, Any]) -> None:
    server = build_server(ExportSource(records["out"]))
    total = await call(server, "explain_number", creek="strawberry-creek", path="visits")
    assert total["value"] == 3 and total["counted_from"] == 3
    assert set(total["resource_ids"]) == {f"Bundle/{v['visit_id']}" for v in records["visits"]}

    people = await call(
        server, "explain_number", creek="strawberry-creek", path="pipes_worth_testing/0/observers"
    )
    assert people["value"] == 2
    assert set(people["resource_ids"]) == {f"Bundle/{v['visit_id']}" for v in records["visits"][:2]}

    note = await call(
        server, "explain_number", creek="strawberry-creek", path="downstream_notes.0.observers"
    )
    assert note["value"] == 2 and note["path"] == "downstream_notes/0/observers"
    assert len(note["resource_ids"]) == 2

    assert "whole section" in await call_error(
        server, "explain_number", creek="strawberry-creek", path="findings"
    )
    assert "no field" in await call_error(
        server, "explain_number", creek="strawberry-creek", path="nothing/here"
    )
    assert "no item" in await call_error(
        server, "explain_number", creek="strawberry-creek", path="findings/9/observers"
    )
    assert "no record" in await call_error(server, "explain_number", creek="nowhere", path="visits")


async def test_the_api_source_reads_the_same_app_over_http(records: dict[str, Any]) -> None:
    """The FastAPI test client is an httpx client, so the API source talks to the real routes."""
    api = ApiSource("http://testserver", client=records["client"])
    exported = build_server(ExportSource(records["out"]))
    live = build_server(api)
    a = await call(exported, "list_creeks")
    b = await call(live, "list_creeks")
    assert a["creeks"] == b["creeks"] and a["resource_ids"] == b["resource_ids"]
    assert b["source"].startswith("read only API at http://testserver")
    ra = await call(exported, "get_creek_record", creek="strawberry-creek")
    rb = await call(live, "get_creek_record", creek="strawberry-creek")
    assert ra["findings"] == rb["findings"] and ra["downstream_notes"] == rb["downstream_notes"]
    assert "no FHIR record" in await call_error(
        live, "get_observer_score", observer="visit-nowhere"
    )
    with pytest.raises(SourceError, match="no record"):
        api.city("nowhere")


async def test_the_server_runs_over_stdio_as_an_agent_would_start_it(
    records: dict[str, Any],
) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "apps.mcp.server", "--export", str(records["out"])],
        cwd=str(ROOT),
    )
    async with Client(params) as mcp_client:
        names = sorted(t.name for t in (await mcp_client.list_tools()).tools)
        result = await mcp_client.call_tool("list_creeks", {})
    assert names == sorted(TOOLS)
    assert not result.is_error
    assert payload(result)["creeks"][0]["creek"] == "strawberry-creek"


def test_an_export_folder_without_creeks_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="creeks.json"):
        ExportSource(tmp_path)
