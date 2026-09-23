"""A read only MCP server over our own records, run locally over stdio (Update 10 tier 2 item 2).

Five tools: list_creeks, get_creek_record, list_findings, get_observer_score, explain_number.
Every answer carries the visit ids and the FHIR Bundle links it was counted from, under
`resource_ids` and `fhir`, so an agent cannot state a number it cannot trace. Nothing here writes,
decides or calls a model. The judgement is in core/act.py; this only reads what it produced.

Run:  uv run python -m apps.mcp.server --export data/export
      uv run python -m apps.mcp.server --api https://second-look-api.thealexschroeder.workers.dev
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from apps.mcp.source import DEFAULT_API, ApiSource, ExportSource, Source, SourceError

INSTRUCTIONS = (
    "Second Look keeps citizen creek checks with the observer's per feature test score. This "
    "server is read only. Every answer lists the visit ids and FHIR Bundle links it was counted "
    "from under resource_ids and fhir. When you state a number from here, give its ids with it. "
    "A finding is something a person reported; passed_observers counts the people among them who "
    "held a passing, unexpired score for that feature. Nothing here is a health claim."
)
TEST_QR_PREFIX = "sl-qr-test-"
PRACTITIONER_PREFIX = "sl-practitioner-"


def _bundle_refs(visit_ids: Sequence[str]) -> list[str]:
    return [f"Bundle/{v}" for v in visit_ids]


def _fhir_links(visit_ids: Sequence[str]) -> list[str]:
    return [f"/api/fhir/Bundle/{v}" for v in visit_ids]


def _with_evidence(payload: dict[str, Any], visit_ids: Sequence[str]) -> dict[str, Any]:
    ids = list(dict.fromkeys(visit_ids))
    payload["resource_ids"] = _bundle_refs(ids)
    payload["fhir"] = _fhir_links(ids)
    return payload


def _resources(bundle: dict[str, Any], resource_type: str) -> list[dict[str, Any]]:
    return [
        e["resource"]
        for e in bundle.get("entry", [])
        if e.get("resource", {}).get("resourceType") == resource_type
    ]


def _walk(node: Any, parts: Sequence[str]) -> list[Any]:
    """Every node on the path, root first. Raises SourceError with the part that failed."""
    trail: list[Any] = [node]
    for part in parts:
        if isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                raise SourceError(f"there is no item {part!r} in that list") from None
        elif isinstance(node, dict):
            if part not in node:
                raise SourceError(f"there is no field {part!r} there")
            node = node[part]
        else:
            raise SourceError(f"{part!r} cannot be looked up inside a plain value")
        trail.append(node)
    return trail


class _PlainErrors:
    """Inside a tool, a SourceError becomes a ToolError, which the SDK hands to the agent with
    its message intact. Any other exception stays hidden behind a generic error, as it should."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, kind: type | None, exc: BaseException | None, _tb: object) -> None:
        if isinstance(exc, SourceError):
            raise ToolError(str(exc)) from exc


def build_server(source: Source) -> MCPServer:
    server = MCPServer(
        name="second-look",
        title="Second Look creek records",
        instructions=INSTRUCTIONS,
        version="0.1.0",
    )

    def city(creek: str) -> dict[str, Any]:
        with _PlainErrors():
            view = source.city(creek)
        view.setdefault("visit_ids", [])
        return view

    @server.tool(description="Every creek with a record, each with the visit ids behind its count.")
    def list_creeks() -> dict[str, Any]:
        with _PlainErrors():
            creeks = source.creeks()
        all_ids = [v for c in creeks for v in c.get("visit_ids", [])]
        return _with_evidence({"source": source.describe(), "creeks": creeks}, all_ids)

    @server.tool(
        description=(
            "One creek's record: what people reported, what the creek needs in approved words, "
            "which pipes are worth testing, its reaches and the downstream notes. Every list "
            "item carries its own visit_ids and fhir links. `creek` is a slug such as "
            "strawberry-creek, or a stored creek id."
        )
    )
    def get_creek_record(creek: str) -> dict[str, Any]:
        view = city(creek)
        return _with_evidence({"source": source.describe(), **view}, view["visit_ids"])

    @server.tool(
        description=(
            "Findings across every creek, or one. Filter by feature id (artificial_bank, "
            "dug_out_channel, invasive_plant, pipe_running, or a form item such as barriers), by "
            "the least number of different people who reported it, and, with passed_only, count "
            "only people who held a passing, unexpired score for that feature."
        )
    )
    def list_findings(
        creek: str | None = None,
        feature: str | None = None,
        min_observers: int = 1,
        passed_only: bool = False,
    ) -> dict[str, Any]:
        if min_observers < 1:
            raise ToolError("min_observers must be at least 1")
        with _PlainErrors():
            targets = [creek] if creek else [c["creek"] for c in source.creeks()]
        found: list[dict[str, Any]] = []
        for key in targets:
            view = city(key)
            for f in view.get("findings", []):
                if feature and f.get("feature") != feature:
                    continue
                count = f.get("passed_observers", 0) if passed_only else f.get("observers", 0)
                if count < min_observers:
                    continue
                found.append(
                    {
                        "creek": view.get("creek_slug") or view.get("creek_id") or key,
                        "creek_name": view.get("creek_name"),
                        **f,
                        "resource_ids": _bundle_refs(f.get("visit_ids", [])),
                    }
                )
        ids = [v for f in found for v in f.get("visit_ids", [])]
        return _with_evidence(
            {
                "source": source.describe(),
                "filters": {
                    "creek": creek,
                    "feature": feature,
                    "min_observers": min_observers,
                    "passed_only": passed_only,
                },
                "findings": found,
            },
            ids,
        )

    @server.tool(
        description=(
            "An observer's test score as the record carries it: the Practitioner's dated "
            "qualification and the per feature k of 4 from the test sitting. `observer` is a "
            "Practitioner id such as sl-practitioner-1a2b3c4d5e6f, or a visit id, whose "
            "observer is then looked up. The person is known only by a hash of a random token."
        )
    )
    def get_observer_score(observer: str) -> dict[str, Any]:
        wanted = observer.removeprefix("Practitioner/")
        bundle: dict[str, Any] | None = None
        visit_id: str | None = None
        with _PlainErrors():
            if not wanted.startswith(PRACTITIONER_PREFIX):
                bundle = source.bundle(wanted)
                visit_id = wanted
            else:
                for c in source.creeks():
                    for vid in c.get("visit_ids", []):
                        candidate = source.bundle(vid)
                        people = _resources(candidate, "Practitioner")
                        if any(p.get("id") == wanted for p in people):
                            bundle, visit_id = candidate, vid
                            break
                    if bundle is not None:
                        break
        if bundle is None:
            raise ToolError(f"no record names the observer {observer!r}")
        practitioners = _resources(bundle, "Practitioner")
        if not practitioners:
            raise ToolError(f"the record {visit_id!r} names no observer")
        practitioner = practitioners[0]
        qualification = (practitioner.get("qualification") or [{}])[0]
        period = qualification.get("period", {})
        scores: list[dict[str, Any]] = []
        for qr in _resources(bundle, "QuestionnaireResponse"):
            if not str(qr.get("id", "")).startswith(TEST_QR_PREFIX):
                continue
            for item in qr.get("item", []):
                answer = (item.get("item") or [{}])[0].get("answer") or [{}]
                scores.append(
                    {
                        "feature": item.get("linkId"),
                        "correct": answer[0].get("valueInteger"),
                        "total": 4,
                    }
                )
        return _with_evidence(
            {
                "source": source.describe(),
                "practitioner_id": practitioner.get("id"),
                "tested_on": period.get("start"),
                "score_counts_until": period.get("end"),
                "scores": scores,
                "scores_note": (
                    "k of 4 per feature, from the test sitting in this record"
                    if scores
                    else "this record carries the qualification period but no per feature score"
                ),
                "from_visit": visit_id,
            },
            [visit_id] if visit_id else [],
        )

    @server.tool(
        description=(
            "The resource ids behind one figure on a creek's record. `path` names the figure: "
            "visits, findings/0/observers, pipes_worth_testing/0, downstream_notes/2/observers, "
            "reaches/3/visits. The answer is the value and the visit ids and fhir links of the "
            "nearest thing on that path that carries evidence."
        )
    )
    def explain_number(creek: str, path: str) -> dict[str, Any]:
        view = city(creek)
        parts = [p for p in path.replace(".", "/").split("/") if p]
        if not parts:
            raise ToolError("say which figure, for example visits or findings/0/observers")
        with _PlainErrors():
            trail = _walk(view, parts)
        value = trail[-1]
        if isinstance(value, dict | list):
            raise ToolError(f"{path!r} is a whole section, not one figure; name a field in it")
        carrier: dict[str, Any] | None = None
        for node in reversed(trail):
            if isinstance(node, dict) and "visit_ids" in node:
                carrier = node
                break
        if carrier is None:
            raise ToolError(f"nothing on the path {path!r} carries visit ids")
        ids = list(carrier.get("visit_ids", []))
        # A reach's own counts are the visits at its spots, which the reach lists through notes
        # only; fall back to the creek's visits so the answer is never empty handed.
        if not ids and trail[0] is not carrier:
            ids = list(view.get("visit_ids", []))
        return _with_evidence(
            {
                "source": source.describe(),
                "creek": view.get("creek_slug") or view.get("creek_id") or creek,
                "path": "/".join(parts),
                "value": value,
                "counted_from": len(ids),
            },
            ids,
        )

    return server


def make_source(argv: Sequence[str] | None = None) -> Source:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    where = parser.add_mutually_exclusive_group()
    where.add_argument("--export", metavar="DIR", help="a folder from scripts/export_records.py")
    where.add_argument("--api", metavar="URL", help=f"our read only API (default {DEFAULT_API})")
    args = parser.parse_args(argv)
    if args.export:
        return ExportSource(args.export)
    return ApiSource(args.api or DEFAULT_API)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        source = make_source(argv)
    except SourceError as exc:
        print(f"second-look mcp: {exc}", file=sys.stderr)
        return 2
    build_server(source).run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
