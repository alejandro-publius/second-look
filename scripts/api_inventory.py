"""Every HTTP route and MCP tool, read from the code, for docs/API.md and docs/MCP.md.

  uv run python scripts/api_inventory.py           writes results/api_inventory.json
  uv run python scripts/api_inventory.py --check   fails when that file is stale

Worker routes come from worker/src/index.ts, read as text: every `path === "..."` test and every
`/^...$/.exec(path)` pattern, with the method the same `if` checks, or "any" when it checks none.
Python routes come from apps/api/*.py, read with ast: every @router.<method>("...") and
@app.<method>("...") decorator, the router's prefix, and the rate limiter in its dependencies.
The limits are the RateLimiter(...) constants in apps/api/security.py. MCP tools are the
functions under @server.tool(...) in apps/mcp/server.py, with their parameters.

scripts/tests/test_api_docs.py compares the same reading with the tables in docs/API.md and
docs/MCP.md, so a route or a tool added without a row fails the tests. The file this writes
holds the counts and limits the docs quote through claim markers (hard rule 12).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "api_inventory.json"
WORKER_INDEX = ROOT / "worker" / "src" / "index.ts"
API_DIR = ROOT / "apps" / "api"
SECURITY = API_DIR / "security.py"
MCP_SERVER = ROOT / "apps" / "mcp" / "server.py"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
ANY = "any"

LITERAL_RE = re.compile(r'path === "([^"]+)"(?:\s*&&\s*request\.method === "([A-Z]+)")?')
PATTERN_RE = re.compile(r"const (\w+) = /\^(.+?)\$/\.exec\(path\);")
PARAM_GROUP = "([^/]+)"


class InventoryError(RuntimeError):
    """The code no longer has the shape this reader expects. Fix the reader, not the code."""


@dataclass(frozen=True, order=True)
class Route:
    path: str
    method: str
    limit: str | None = None
    source: str = ""


def template(path: str) -> str:
    """A path with every parameter written as {}: /api/spot/{spot_id} and the regex agree."""
    return re.sub(r"\{[^}]*\}", "{}", path)


def _pattern_to_path(pattern: str) -> str:
    path = pattern.replace(PARAM_GROUP, "{}").replace("\\/", "/")
    if "\\" in path or "(" in path or "[" in path:
        raise InventoryError(
            f"a Worker route pattern this reader cannot turn into a path: {pattern}"
        )
    return path


def worker_routes(text: str) -> list[Route]:
    """Every route worker/src/index.ts answers, with the method it checks or "any"."""
    routes: set[Route] = set()
    for m in LITERAL_RE.finditer(text):
        routes.add(Route(m.group(1), m.group(2) or ANY, source="worker/src/index.ts"))
    for m in PATTERN_RE.finditer(text):
        var, pattern = m.group(1), m.group(2)
        uses = re.findall(
            rf"if \({re.escape(var)}(?:\s*&&\s*request\.method === \"([A-Z]+)\")?\)", text
        )
        if not uses:
            raise InventoryError(f"the Worker pattern {var} is made but never tested in an if")
        for method in uses:
            routes.add(
                Route(_pattern_to_path(pattern), method or ANY, source="worker/src/index.ts")
            )
    if not routes:
        raise InventoryError("no route found in worker/src/index.ts")
    return sorted(routes)


def _limiter_of(call: ast.Call) -> str | None:
    """The limiter name in dependencies=[Depends(rate_limited(NAME))], or None."""
    for kw in call.keywords:
        if kw.arg != "dependencies" or not isinstance(kw.value, ast.List):
            continue
        for dep in kw.value.elts:
            if (
                isinstance(dep, ast.Call)
                and dep.args
                and isinstance(dep.args[0], ast.Call)
                and isinstance(dep.args[0].func, ast.Name)
                and dep.args[0].func.id == "rate_limited"
                and dep.args[0].args
                and isinstance(dep.args[0].args[0], ast.Name)
            ):
                return dep.args[0].args[0].id
    return None


def _prefixes(tree: ast.Module) -> dict[str, str]:
    """Router and app variables in one module, with their prefix."""
    out: dict[str, str] = {}
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        func = node.value.func
        name = func.id if isinstance(func, ast.Name) else None
        if name not in {"APIRouter", "FastAPI"}:
            continue
        prefix = ""
        for kw in node.value.keywords:
            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                prefix = str(kw.value.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                out[target.id] = prefix
    return out


def python_routes(api_dir: Path = API_DIR) -> list[Route]:
    """Every route the FastAPI app in apps/api defines, with its rate limiter."""
    routes: list[Route] = []
    for path in sorted(api_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        prefixes = _prefixes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for dec in node.decorator_list:
                if not (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and isinstance(dec.func.value, ast.Name)
                    and dec.func.value.id in prefixes
                    and dec.func.attr in HTTP_METHODS
                ):
                    continue
                if not (dec.args and isinstance(dec.args[0], ast.Constant)):
                    raise InventoryError(f"{path.name}:{dec.lineno}: a route path that is not text")
                full = prefixes[dec.func.value.id] + str(dec.args[0].value)
                routes.append(
                    Route(
                        full,
                        dec.func.attr.upper(),
                        _limiter_of(dec),
                        path.relative_to(ROOT).as_posix()
                        if path.is_relative_to(ROOT)
                        else path.name,
                    )
                )
    if not routes:
        raise InventoryError("no route found in apps/api")
    return sorted(routes)


def limiter_label(name: str) -> str:
    """STUDY_LIMIT is written "study" in the docs."""
    return name.removesuffix("_LIMIT").lower()


def rate_limits(security: Path = SECURITY) -> dict[str, dict[str, int | float]]:
    tree = ast.parse(security.read_text(encoding="utf-8"))
    out: dict[str, dict[str, int | float]] = {}
    for node in tree.body:
        if not (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "RateLimiter"
        ):
            continue
        values = {
            kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords if kw.arg is not None
        }
        for target in node.targets:
            if isinstance(target, ast.Name):
                out[limiter_label(target.id)] = {
                    "limit": values["limit"],
                    "window_seconds": values["window_seconds"],
                }
    if not out:
        raise InventoryError("no RateLimiter constant found in apps/api/security.py")
    return out


def mcp_tools(server: Path = MCP_SERVER) -> list[dict[str, Any]]:
    """Every function registered with @server.tool(...), with its parameters."""
    tree = ast.parse(server.read_text(encoding="utf-8"))
    tools: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for dec in node.decorator_list:
            call = dec if isinstance(dec, ast.Call) else None
            func = call.func if call else dec
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "tool"
                and isinstance(func.value, ast.Name)
                and func.value.id == "server"
            ):
                continue
            args = node.args.args
            defaults = [None] * (len(args) - len(node.args.defaults)) + list(node.args.defaults)
            params = [
                {
                    "name": a.arg,
                    "type": ast.unparse(a.annotation) if a.annotation else "",
                    "default": ast.unparse(d) if d is not None else None,
                }
                for a, d in zip(args, defaults, strict=True)
            ]
            tools.append({"name": node.name, "params": params})
    if not tools:
        raise InventoryError("no @server.tool function found in apps/mcp/server.py")
    return sorted(tools, key=lambda t: str(t["name"]))


def inventory() -> dict[str, Any]:
    worker = worker_routes(WORKER_INDEX.read_text(encoding="utf-8"))
    python = python_routes()
    tools = mcp_tools()
    return {
        "script": "scripts/api_inventory.py",
        "synthetic": False,
        "worker": {
            "count": len(worker),
            "routes": [{"method": r.method, "path": r.path} for r in worker],
        },
        "python": {
            "count": len(python),
            "routes": [
                {
                    "method": r.method,
                    "path": r.path,
                    "limit": limiter_label(r.limit) if r.limit else None,
                    "file": r.source,
                }
                for r in python
            ],
            "with_a_rate_limit": sum(1 for r in python if r.limit),
        },
        "rate_limits": rate_limits(),
        "mcp": {"count": len(tools), "tools": tools},
    }


def render(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="fail when the file is stale")
    args = parser.parse_args(argv)
    try:
        text = render(inventory())
    except InventoryError as exc:
        print(f"api-inventory: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(
                "api-inventory: results/api_inventory.json is stale; run scripts/api_inventory.py"
            )
            return 1
        print("api-inventory: results/api_inventory.json matches the code")
        return 0
    OUT.write_text(text, encoding="utf-8")
    doc = json.loads(text)
    print(
        f"api-inventory: {doc['worker']['count']} Worker routes, {doc['python']['count']} Python "
        f"routes, {doc['mcp']['count']} MCP tools into {OUT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
