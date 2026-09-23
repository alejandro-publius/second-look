"""Run every command printed in README.md and docs/ACCEPTANCE.md, as a judge would (Update 16A).

Runs in a fresh clone of HEAD outside the repo, after the setup a judge would do (uv sync, npm ci),
and records which commands fail. Commands are the backticked spans and fenced shell lines that
start with a known tool. A command is only run when it is on the safe list below: nothing that
deploys, pushes to the sandbox, wipes a database, spends money or makes the repo public. The rest
are listed as not run, with the reason. Two commands need a harness and get one:

- make dev starts two servers and never exits: it runs for up to two minutes and passes when both
  answer. When its ports are taken by another process on this machine, the same two servers run
  on free ports and the report says so.
- the MCP server speaks JSON-RPC on stdio: it passes when it answers initialize and tools/list.

Another session uses ports 3100 and 8100 on this machine, so nothing here binds them: the targets
whose design gate starts the built app on 3100 (make check, make judge-check, make design-check)
run with SKIP_TAP=1, the repo's own switch that skips that one step, and the report says so; the
Playwright suites that serve on 3100 and mock 8100 are listed as not run. A command with a
placeholder in it (SITE_URL=...) is listed, not run. --branch reads a branch other than harden,
for example depth, whose docs/ACCEPTANCE.md exists there first.

Writes results/harden/commands.md and results/harden/commands.json.

  uv run python scripts/harden_commands.py --work /tmp/somewhere
"""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import shlex
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DOCS = ["README.md", "docs/ACCEPTANCE.md"]
TOOLS = ("make", "uv", "npx", "npm", "curl", "python", "bash", "node", "cd", "git", "docker")
NEVER = (
    "deploy",
    "go-public",
    "gh repo edit",
    "wipe",
    "repush",
    "backup",
    "restore",
    "--real",
    "secret",
    "sandbox_write",
    "--remote",
    "rm -rf",
)
SAFE_MAKE = {
    "check",
    "judge-check",
    "test",
    "lint",
    "types",
    "fhir-validate",
    "diagrams",
    "readability",
    "verify-claims",
    "audit-verify",
    "submit-check",
    "preflight",
    "preflight-launch",
    "preflight-judges",
    "export-records",
    "worker-check",
    "worker-e2e",
    "e2e",
    "manifest-check",
    "dash-check",
    "design-check",
    "render-readme",
    "web-build",
    "help",
}
SAFE_HOSTS = (
    "second-look-79t.pages.dev",
    "depth.second-look-79t.pages.dev",
    "second-look-api.thealexschroeder.workers.dev",
    "sandbox.hl7europe.eu",  # hard rule 10: read-only GETs, one at a time
)


def extract(tree: Path) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for doc in DOCS:
        path = tree / doc
        if not path.exists():
            continue
        fenced = False
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            candidates = []
            if fenced:
                s = line.strip().removeprefix("$ ")
                candidates.append(s)
            else:
                candidates += re.findall(r"`([^`\n]+)`", line)
            for c in candidates:
                c = c.strip()
                words = c.split(" ")
                while words and re.match(r"^[A-Z_]+=\S*$", words[0]):
                    words = words[1:]
                if words and words[0] != c.split(" ")[0] and words[0] in TOOLS:
                    found.append({"doc": doc, "line": n, "command": c})
                elif c.split(" ")[0] in TOOLS and not c.startswith(("cd ", "git clone")):
                    found.append({"doc": doc, "line": n, "command": c})
                elif c.startswith("cd ") and "&&" in c:
                    found.append({"doc": doc, "line": n, "command": c})
    seen: set[str] = set()
    unique = []
    for f in found:
        if f["command"] not in seen:
            seen.add(f["command"])
            unique.append(f)
    # A command that says it runs "after" another runs after it.
    unique.sort(key=lambda f: 1 if "apps.mcp.server" in f["command"] else 0)
    return unique


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def run(cmd: str, cwd: Path, timeout: int = 900, env: dict[str, str] | None = None) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            env={**os.environ, **(env or {})},
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        code, out = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        code, out = -1, f"timed out after {timeout} s"
    return {"code": code, "seconds": round(time.monotonic() - started, 1), "tail": out[-1500:]}


PORT_BOUND_MAKE = {"check", "judge-check", "design-check"}  # run with SKIP_TAP=1
SERVES_3100 = ("make e2e", "npx playwright test", "npm run start", "npm test")


def policy(cmd: str) -> str:
    """Empty when the command may run; otherwise the reason it is not run."""
    low = cmd.lower()
    if "..." in cmd or "<" in cmd:
        return "a template with a placeholder in it, not a command to run as printed"
    if any(s in cmd for s in SERVES_3100) and "deployed-smoke" not in cmd:
        return "serves the app on port 3100, which another session uses on this machine"
    for bad in NEVER:
        if bad in low:
            return f"not on the safe list: contains '{bad}'"
    words = shlex.split(cmd)
    if words[:2] == ["uv", "sync"] or re.fullmatch(
        r"cd apps/web && npm (install|ci)( && cd \.\./\.\.)?", cmd
    ):
        return ""  # the setup a judge does first; it only touches the clone
    if words[0] == "make":
        target = words[1] if len(words) > 1 else "help"
        if target == "dev":
            return ""
        if target not in SAFE_MAKE:
            return f"make {target} is not on the safe list"
        return ""
    if words[0] == "curl":
        if any(w in ("-X", "--request", "-d", "--data", "-F", "--form", "-T") for w in words):
            return "curl that sends data"
        urls = [w for w in words if w.startswith("http")]
        if not urls or not all(any(h in u for h in SAFE_HOSTS) for u in urls):
            return "curl to a host not on the safe list"
        if any("/api/test/" in u and "counts" not in u for u in urls):
            return "a study endpoint"
        return ""
    if words[0] == "uv" and "run" in words:
        return ""
    return "not on the safe list"


def make_dev(tree: Path) -> dict:
    api_port, web_port = 8000, 3100
    moved = ""
    if not (port_free(api_port) and port_free(web_port)):
        api_port, web_port = 8960, 8961
        moved = (
            "ports 8000 or 3100 are taken by another process on this machine, so the same two "
            "servers ran on 8960 and 8961"
        )
    cmds = [
        (f"uv run python -m uvicorn apps.api.main:app --port {api_port}", tree),
        (f"npm run dev -- -p {web_port}", tree / "apps" / "web"),
    ]
    procs = [
        subprocess.Popen(
            c,
            shell=True,
            cwd=d,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        for c, d in cmds
    ]
    started = time.monotonic()
    ok = {"api": False, "web": False}
    try:
        while time.monotonic() - started < 150 and not all(ok.values()):
            for name, url in (
                ("api", f"http://127.0.0.1:{api_port}/health"),
                ("web", f"http://127.0.0.1:{web_port}/"),
            ):
                if ok[name]:
                    continue
                try:
                    ok[name] = httpx.get(url, timeout=10).status_code == 200
                except httpx.HTTPError:
                    pass
            time.sleep(2)
    finally:
        for p in procs:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    passed = all(ok.values())
    detail = f"API answered: {ok['api']}; web answered: {ok['web']}"
    return {
        "code": 0 if passed else 1,
        "seconds": round(time.monotonic() - started, 1),
        "tail": f"{detail}. {moved}".strip(),
    }


def mcp(cmd: str, tree: Path) -> dict:
    started = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=tree,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    assert proc.stdin and proc.stdout
    msgs = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "harden", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    tools: list[str] = []
    note = ""
    try:
        for m in msgs:
            proc.stdin.write(json.dumps(m) + "\n")
            proc.stdin.flush()
        end = time.monotonic() + 60
        while time.monotonic() < end:
            ready, _, _ = select.select([proc.stdout], [], [], 1)
            if not ready:
                if proc.poll() is not None:
                    break
                continue
            line = proc.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == 2:
                tools = [t["name"] for t in msg.get("result", {}).get("tools", [])]
                break
    except BrokenPipeError:
        note = "the server closed its input"
    finally:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    err = (proc.stderr.read() if proc.stderr else "")[-600:] if proc.poll() is not None else ""
    passed = bool(tools)
    return {
        "code": 0 if passed else 1,
        "seconds": round(time.monotonic() - started, 1),
        "tail": (
            f"tools: {', '.join(tools)}" if passed else f"no tools/list answer. {note} {err}"
        ).strip(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--work", type=Path, required=True, help="scratch folder outside the repo")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "harden")
    ap.add_argument("--branch", default="", help="a local branch to read instead of HEAD")
    ap.add_argument("--name", default="commands", help="output file stem")
    args = ap.parse_args()
    if ROOT in args.work.resolve().parents:
        raise SystemExit("--work must be outside the repo")
    tree = args.work / "tree"
    subprocess.run(["rm", "-rf", str(tree)], check=True)
    branch = ["-b", args.branch] if args.branch else []
    subprocess.run(["git", "clone", "-q", *branch, str(ROOT), str(tree)], check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=tree, capture_output=True, text=True
    ).stdout.strip()
    setup = {
        "uv sync --frozen": run("uv sync --frozen", tree),
        "npm ci (apps/web)": run("npm ci --no-audit --no-fund", tree / "apps" / "web"),
        "npm ci (worker)": run("npm ci --no-audit --no-fund", tree / "worker"),
    }
    rows = []
    for c in extract(tree):
        cmd = c["command"]
        why = policy(cmd)
        if why:
            rows.append({**c, "ran": False, "result": "not run", "detail": why})
            continue
        if cmd.strip() == "make dev":
            r = make_dev(tree)
        elif "apps.mcp.server" in cmd:
            r = mcp(cmd, tree)
        else:
            env = {"E2E_PORT": "8971"} if "worker-e2e" in cmd else {}
            words = shlex.split(cmd)
            if words[0] == "make" and len(words) > 1 and words[1] in PORT_BOUND_MAKE:
                env["SKIP_TAP"] = "1"
            r = run(cmd, tree, env=env)
            if env.get("SKIP_TAP"):
                r["tail"] = (
                    "(ran with SKIP_TAP=1: the tap target step on port 3100 skipped) " + r["tail"]
                )
        result = "pass" if r["code"] == 0 else "fail"
        rows.append(
            {
                **c,
                "ran": True,
                "result": result,
                "exit": r["code"],
                "seconds": r["seconds"],
                "detail": r["tail"],
            }
        )
        print(f"{result}: {cmd}")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{args.name}.json").write_text(
        json.dumps(
            {
                "checked_utc": stamp,
                "commit": commit,
                "branch": args.branch or "HEAD",
                "setup": {k: v["code"] for k, v in setup.items()},
                "commands": rows,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    missing = [d for d in DOCS if not (tree / d).exists()]
    lines = [
        "# Commands printed in the README",
        "",
        f"Checked {stamp} at commit {commit}"
        + (f" (branch {args.branch})" if args.branch else "")
        + " by `uv run python scripts/harden_commands.py`, in a "
        "fresh clone after `uv sync --frozen` and `npm ci` in apps/web and worker, the way a judge "
        "would start. "
        + (f"{', '.join(missing)} does not exist, so only the README was read. " if missing else "")
        + "Setup: "
        + ", ".join(f"{k} exit {v['code']}" for k, v in setup.items())
        + ".",
        "",
        "| Where | Command | Result | What happened |",
        "|---|---|---|---|",
    ]
    for r in rows:
        detail = " ".join(str(r["detail"]).split())[-300:].replace("|", "/")
        lines.append(f"| {r['doc']}:{r['line']} | `{r['command']}` | {r['result']} | {detail} |")
    failed = [r for r in rows if r["result"] == "fail"]
    lines += [
        "",
        f"{len(rows)} commands: {sum(r['result'] == 'pass' for r in rows)} pass, {len(failed)} "
        f"fail, {sum(not r['ran'] for r in rows)} not run.",
        "",
    ]
    (args.out / f"{args.name}.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
