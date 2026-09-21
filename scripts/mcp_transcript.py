"""Write examples/mcp/transcript.md: one short, real session against the MCP server.

  uv run python scripts/mcp_transcript.py

Everything in the transcript is produced by running the code: a throwaway database and store in
a temp folder, two people who passed the pipe feature reporting a pipe at the Faculty Glade pin,
one quiet visit in the park downstream, an export, then the five tools called through the MCP
client in memory. Ids differ from run to run because spot and visit ids are random; the shape and
the numbers do not.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "mcp" / "transcript.md"
MAX_LINES = 60


def _prepare_environment(tmp: Path) -> None:
    """The API reads its settings once, before it is imported. Same trick as the API tests."""
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/transcript.db"
    os.environ["FHIR_STORE_DIR"] = str(tmp / "fhir_store")
    os.environ["UPLOAD_DIR"] = str(tmp / "uploads")
    os.environ["AUDIT_LOG_PATH"] = str(tmp / "audit.jsonl")
    os.environ["EXPORT_TOKEN"] = "transcript-export-token-000000"
    os.environ["QA_KEY"] = "transcript-qa-key-00000000000"
    os.environ["PUBLIC_WEB_ORIGIN"] = "http://web.test"
    os.environ["RANDOMIZATION_SEED"] = "transcript-seed"
    os.environ["BUILD_HASH"] = "transcript"


def _clip(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= MAX_LINES:
        return text
    kept = lines[:MAX_LINES]
    return "\n".join(kept) + f"\n... {len(lines) - MAX_LINES} more lines"


async def _run(export_dir: Path, visits: list[dict[str, Any]]) -> list[tuple[str, dict, Any]]:
    from mcp.client import Client

    from apps.mcp.server import build_server
    from apps.mcp.source import ExportSource

    server = build_server(ExportSource(export_dir))
    calls: list[tuple[str, dict[str, Any]]] = [
        ("list_creeks", {}),
        ("list_findings", {"feature": "pipe_running", "min_observers": 2, "passed_only": True}),
        (
            "explain_number",
            {"creek": "strawberry-creek", "path": "pipes_worth_testing/0/observers"},
        ),
        ("get_observer_score", {"observer": visits[0]["visit_id"]}),
        ("get_creek_record", {"creek": "strawberry-creek"}),
        ("explain_number", {"creek": "strawberry-creek", "path": "findings"}),
    ]
    out: list[tuple[str, dict, Any]] = []
    async with Client(server) as client:
        for name, arguments in calls:
            result = await client.call_tool(name, arguments)
            if result.is_error:
                out.append((name, arguments, {"error": result.content[0].text}))  # type: ignore[union-attr]
            else:
                data = result.structured_content
                out.append((name, arguments, data if data is not None else result.content))
    return out


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="sl-mcp-transcript-"))
    _prepare_environment(tmp)

    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from apps.api import core_calls, deps
    from apps.api.db import engine, init_db
    from apps.api.main import app
    from apps.api.tests.test_city import (
        GOOD_ANSWERS,
        PARK_PIN,
        QUIET_ANSWERS,
        SOUTH_FORK_PIN,
        _dry,
        a_visit,
        passing_session,
    )
    from scripts.export_records import export

    now = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)
    core_calls.rain_status = _dry  # no network in a transcript
    app.dependency_overrides[deps.get_now] = lambda: now
    init_db()
    with TestClient(app) as client:
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
    export_dir = tmp / "export"
    with Session(engine) as db:
        counts = export(db, export_dir, now=now)

    results = asyncio.run(_run(export_dir, [first, second, quiet]))
    lines = [
        "# One session with the Second Look MCP server",
        "",
        f"Written by `scripts/mcp_transcript.py` on {datetime.now(UTC):%Y-%m-%d}. Real code, a",
        "throwaway database: two people who passed the pipe feature reported a pipe running",
        "after dry weather at the Faculty Glade pin on Strawberry Creek, and one anonymous visit",
        f"in Strawberry Creek Park, three reaches below, reported nothing. Export: {counts}.",
        "",
        "Start the server the way an agent would:",
        "",
        "```",
        "uv run python -m apps.mcp.server --export data/export",
        "```",
        "",
        "Every answer ends with `resource_ids` and `fhir`: the visit Bundles it was counted from.",
        "",
    ]
    for name, arguments, data in results:
        lines.append(f"## {name}({json.dumps(arguments)[1:-1]})")
        lines.append("")
        lines.append("```json")
        lines.append(_clip(json.dumps(data, indent=2, default=str)))
        lines.append("```")
        lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # The temp folder's name means nothing to a reader.
    OUT.write_text("\n".join(lines).replace(str(tmp), "<temp>"), encoding="utf-8")
    print(f"mcp-transcript: {len(results)} calls into {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
