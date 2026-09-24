"""Every environment variable and setting the code reads, for the table in DEPLOY.md.

  uv run python scripts/config_inventory.py    prints each name with the files that read it

Where it looks:

- Python outside the tests: os.environ.get("X"), os.environ["X"] (reads, not writes),
  environ.get("X") on a passed in mapping, os.getenv("X").
- apps/api/settings.py: every field of Settings, read from the environment in capitals.
- The Worker: the fields of `interface Env` in worker/src/index.ts, and env.X in the Pages
  Functions under apps/web/functions.
- The web app and the Worker's tests: process.env.X.
- Shell scripts: ${X:-default}, unless the script set X itself before it read it.

scripts/tests/test_deploy_config.py fails when a name found here has no row in DEPLOY.md.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_DIRS = ("core", "apps", "evals", "scripts")
PY_PATTERNS = (
    re.compile(r"os\.environ\.get\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
    re.compile(r"os\.environ\[\s*[\"']([A-Z][A-Z0-9_]+)[\"']\s*\](?!\s*=[^=])"),
    re.compile(r"(?<![\w.])environ\.get\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
    re.compile(r"os\.getenv\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
)
PROCESS_ENV = re.compile(r"process\.env\.([A-Z][A-Z0-9_]+)|process\.env\[\s*[\"']([A-Z0-9_]+)")
FUNCTION_ENV = re.compile(r"\benv\.([A-Z][A-Z0-9_]+)")
SHELL_DEFAULT = re.compile(r"\$\{([A-Z][A-Z0-9_]+):-")
WEB_SKIP = {"node_modules", ".next", "out", "generated", "test-results", "playwright-report"}


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def python_reads() -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for top in PY_DIRS:
        for path in (ROOT / top).rglob("*.py"):
            parts = set(path.relative_to(ROOT).parts)
            if "tests" in parts or "node_modules" in parts or "web" in parts:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in PY_PATTERNS:
                for name in pattern.findall(text):
                    found[name].add(_rel(path))
    return found


def settings_fields(path: Path | None = None) -> dict[str, set[str]]:
    path = path or ROOT / "apps" / "api" / "settings.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, set[str]] = defaultdict(set)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    if item.target.id != "model_config":
                        found[item.target.id.upper()].add(_rel(path))
    return found


def worker_env(index: Path | None = None) -> dict[str, set[str]]:
    index = index or ROOT / "worker" / "src" / "index.ts"
    text = index.read_text(encoding="utf-8")
    block = re.search(r"export interface Env \{(.*?)\n\}", text, re.S)
    if block is None:
        raise SystemExit("config-inventory: no `export interface Env` in worker/src/index.ts")
    found: dict[str, set[str]] = defaultdict(set)
    for name in re.findall(r"^\s*([A-Z][A-Z0-9_]+)\??:", block.group(1), re.M):
        found[name].add(_rel(index))
    for path in (ROOT / "apps" / "web" / "functions").rglob("*.js"):
        for name in FUNCTION_ENV.findall(path.read_text(encoding="utf-8")):
            found[name].add(_rel(path))
    return found


def _web_files() -> list[Path]:
    out: list[Path] = []
    for path in (ROOT / "apps" / "web").rglob("*"):
        if WEB_SKIP & set(path.relative_to(ROOT).parts):
            continue
        if path.suffix in {".ts", ".tsx", ".mjs", ".js"} and path.is_file():
            out.append(path)
    out.extend((ROOT / "worker" / "test").glob("*.mjs"))
    return out


def process_env() -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for path in _web_files():
        for a, b in PROCESS_ENV.findall(path.read_text(encoding="utf-8")):
            found[a or b].add(_rel(path))
    return found


def shell_defaults() -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for path in sorted((ROOT / "scripts").glob("*.sh")):
        lines = path.read_text(encoding="utf-8").splitlines()
        assigned: set[str] = set()
        for line in lines:
            for name in SHELL_DEFAULT.findall(line):
                if name not in assigned:
                    found[name].add(_rel(path))
            m = re.match(r"^\s*([A-Z][A-Z0-9_]+)=", line)
            if m:
                assigned.add(m.group(1))
    return found


def inventory() -> dict[str, set[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for part in (python_reads(), settings_fields(), worker_env(), process_env(), shell_defaults()):
        for name, files in part.items():
            merged[name] |= files
    return dict(sorted(merged.items()))


def main() -> int:
    for name, files in inventory().items():
        print(f"{name}: {', '.join(sorted(files))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
