"""docs/API.md and docs/MCP.md list every route and every tool the code has, and nothing else.

The routes and tools are read out of the code by scripts/api_inventory.py (text for the Worker,
ast for the Python API and the MCP server), then compared with the rows of the tables. A route or
a tool added without a row fails here, and so does a row left behind after one is removed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts import api_inventory as inv

ROOT = Path(__file__).resolve().parents[2]
API_DOC = ROOT / "docs" / "API.md"
MCP_DOC = ROOT / "docs" / "MCP.md"
ROW_RE = re.compile(r"^\|\s*([A-Za-z]+)\s*\|\s*`([^`]+)`\s*\|(.*)\|\s*$")


def section(text: str, heading: str) -> str:
    """The text under one '## heading', up to the next '## '."""
    start = text.index(f"\n## {heading}")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def rows(block: str) -> dict[tuple[str, str], list[str]]:
    """(method, path template) to the other cells, for every route row in a block."""
    out: dict[tuple[str, str], list[str]] = {}
    for line in block.splitlines():
        m = ROW_RE.match(line.strip())
        if not m or not m.group(2).startswith("/"):
            continue
        key = (m.group(1), inv.template(m.group(2)))
        assert key not in out, f"two rows for {key}"
        out[key] = [c.strip() for c in m.group(3).split("|")]
    return out


def worker_code() -> set[tuple[str, str]]:
    text = inv.WORKER_INDEX.read_text(encoding="utf-8")
    return {(r.method, inv.template(r.path)) for r in inv.worker_routes(text)}


def python_code() -> dict[tuple[str, str], str | None]:
    return {(r.method, inv.template(r.path)): r.limit for r in inv.python_routes()}


def test_every_worker_route_has_a_row_and_every_row_a_route() -> None:
    documented = set(rows(section(API_DOC.read_text(encoding="utf-8"), "The Worker")))
    code = worker_code()
    assert code - documented == set(), "Worker routes with no row in docs/API.md"
    assert documented - code == set(), "rows in docs/API.md for no Worker route"


def test_every_python_route_has_a_row_and_every_row_a_route() -> None:
    documented = set(rows(section(API_DOC.read_text(encoding="utf-8"), "The Python API")))
    code = set(python_code())
    assert code - documented == set(), "Python routes with no row in docs/API.md"
    assert documented - code == set(), "rows in docs/API.md for no Python route"


def test_each_python_row_names_the_limiter_the_code_uses() -> None:
    documented = rows(section(API_DOC.read_text(encoding="utf-8"), "The Python API"))
    for key, limit in python_code().items():
        cell = documented[key][-1]
        want = inv.limiter_label(limit) if limit else "none"
        assert re.match(rf"{want}\b", cell), f"{key}: the limit cell says {cell!r}, code {want!r}"


def test_the_limit_legend_lists_every_limiter() -> None:
    legend = section(API_DOC.read_text(encoding="utf-8"), "The Python API")
    for label in inv.rate_limits():
        assert re.search(rf"^\| {label} \| .*rate_limits/{label}/limit", legend, re.M), label


def test_every_mcp_tool_has_a_row_with_all_its_inputs() -> None:
    text = MCP_DOC.read_text(encoding="utf-8")
    documented: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*`(\w+)`\s*\|([^|]*)\|", line.strip())
        if m:
            documented[m.group(1)] = m.group(2)
    tools = {t["name"]: t for t in inv.mcp_tools()}
    assert set(tools) == set(documented), "docs/MCP.md and apps/mcp/server.py disagree"
    for name, tool in tools.items():
        for param in tool["params"]:
            assert f"`{param['name']}`" in documented[name], f"{name}: `{param['name']}` missing"
        if not tool["params"]:
            assert documented[name].strip() == "none", name


def test_the_worker_reader_sees_methods_patterns_and_a_new_route() -> None:
    text = (
        'if (path === "/health") return x;\n'
        'if (path === "/api/upload" && request.method === "POST") return y;\n'
        "const photo = /^\\/api\\/photo\\/([^/]+)$/.exec(path);\n"
        'if (photo && request.method === "GET") return z;\n'
        "const city = /^\\/api\\/city\\/([^/]+)$/.exec(path);\n"
        "if (city) return w;\n"
    )
    got = {(r.method, r.path) for r in inv.worker_routes(text)}
    assert got == {
        ("any", "/health"),
        ("POST", "/api/upload"),
        ("GET", "/api/photo/{}"),
        ("any", "/api/city/{}"),
    }


def test_a_worker_pattern_that_is_never_tested_is_an_error() -> None:
    with pytest.raises(inv.InventoryError):
        inv.worker_routes("const lost = /^\\/api\\/lost$/.exec(path);\n")


def test_the_python_reader_sees_prefix_method_and_limiter(tmp_path: Path) -> None:
    (tmp_path / "r.py").write_text(
        "router = APIRouter(prefix='/api')\n"
        "@router.get('/x/{a}', dependencies=[Depends(rate_limited(READ_LIMIT))])\n"
        "def x(a): ...\n"
        "app = FastAPI()\n"
        "@app.post('/health')\n"
        "async def h(): ...\n",
        encoding="utf-8",
    )
    got = {(r.method, r.path, r.limit) for r in inv.python_routes(tmp_path)}
    assert got == {("GET", "/api/x/{a}", "READ_LIMIT"), ("POST", "/health", None)}


def test_the_committed_inventory_matches_the_code() -> None:
    committed = (ROOT / "results" / "api_inventory.json").read_text(encoding="utf-8")
    assert committed == inv.render(inv.inventory()), "run scripts/api_inventory.py"
