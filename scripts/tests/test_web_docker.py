"""The web image in docker compose matches what next.config.ts makes it build.

next.config.ts sets the tracing root to the repository root so the walks can use the Worker's
pure core. That moves the standalone server under apps/web/ and needs worker/src/core in the
build. The image once kept the old paths: its CMD pointed at a server.js that was not there.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "web"
DOCKERFILE = WEB / "Dockerfile"

# Loads next.config.ts as Next would see it, with the headers helper stubbed, and prints the root
# Next traces from. Next sets outputFileTracingRoot and turbopack.root to one value, the first set.
CONFIG = r"""
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const src = fs.readFileSync("next.config.ts", "utf8");
const options = { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 };
const out = ts.transpileModule(src, { compilerOptions: options }).outputText;
const stubs = {
  "node:path": path,
  "./security-headers.mjs": { buildHeaders: () => ({ everywhere: [] }) },
};
const mod = { exports: {} };
const req = (name) => stubs[name] ?? {};
const run = new Function("require", "module", "exports", "__dirname", out);
run(req, mod, mod.exports, process.cwd());
const config = mod.exports.default;
const root = config.outputFileTracingRoot ?? (config.turbopack ?? {}).root ?? process.cwd();
process.stdout.write(JSON.stringify({ output: config.output, root }));
"""


def traced_root() -> Path:
    if shutil.which("node") is None or not (WEB / "node_modules" / "typescript").exists():
        pytest.skip("needs node and apps/web/node_modules: run npm ci in apps/web")
    done = subprocess.run(
        ["node", "-e", CONFIG], cwd=WEB, capture_output=True, text=True, timeout=60, check=False
    )
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout)
    assert got["output"] == "standalone"
    return Path(got["root"]).resolve()


def stages() -> tuple[list[str], list[str]]:
    """The build stage's lines and the run stage's lines."""
    lines = [ln.strip() for ln in DOCKERFILE.read_text(encoding="utf-8").splitlines()]
    starts = [i for i, ln in enumerate(lines) if ln.upper().startswith("FROM ")]
    assert len(starts) == 2, "expected a build stage and a run stage"
    return lines[starts[0] : starts[1]], lines[starts[1] :]


def test_the_image_runs_the_server_where_the_standalone_build_puts_it() -> None:
    app = WEB.resolve().relative_to(traced_root()).as_posix()
    prefix = "" if app == "." else f"{app}/"
    _, run = stages()
    assert f'CMD ["node", "{prefix}server.js"]' in run
    assert "COPY --from=build /repo/apps/web/.next/standalone ./" in run
    assert f"COPY --from=build /repo/apps/web/.next/static ./{prefix}.next/static" in run
    assert f"COPY --from=build /repo/apps/web/public ./{prefix}public" in run


def outside_imports() -> set[str]:
    """Every repo directory outside apps/web that the web app's own code imports from."""
    found: set[str] = set()
    for p in [
        *WEB.glob("app/**/*.ts*"),
        *WEB.glob("components/**/*.ts*"),
        *WEB.glob("lib/**/*.ts"),
    ]:
        for spec in re.findall(r"""from\s+["'](\.[^"']*)["']""", p.read_text(encoding="utf-8")):
            # normpath, not resolve: a symlinked generated/ must not count as outside.
            target = Path(os.path.normpath(p.parent / spec))
            if not target.is_relative_to(WEB):
                found.add(target.parent.relative_to(ROOT).as_posix())
    return found


def test_the_build_stage_copies_everything_the_web_app_imports_from_outside_it() -> None:
    needed = outside_imports()
    assert "worker/src/core" in needed, "the walks no longer import the Worker's core"
    build, _ = stages()
    copied = [
        ln.split()[1].rstrip("/") for ln in build if ln.startswith("COPY ") and "--from" not in ln
    ]
    ignored = [
        ln.strip().rstrip("/")
        for ln in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    for d in sorted(needed):
        assert any(d == c or d.startswith(f"{c}/") or c == "." for c in copied), d
        assert not any(d == i or d.startswith(f"{i}/") for i in ignored), d
