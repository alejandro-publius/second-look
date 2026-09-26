"""One command a judge can run: no key, no network, six lines out (Update 10 tier 3 item 11).

    make judge-check

It proves, from a clean checkout and nothing else, that the things this repository claims are
in it really are. Every step runs offline. The API key is removed from the environment before
anything starts, so a step that quietly wanted to call a model fails here instead of passing on
somebody's credit.

The six steps:

1. Tests. The whole Python suite and the Worker's golden vector suite.
2. Reproduce. make reproduce grades the AI numbers in results/ again from the raw model replies
   committed in evals/fixtures/raw/ and the synthetic ones from their seeds, and fails if one
   differs (UPDATE_29 section 4). Not every number can be: the two paid benchmark runs kept counts,
   not replies, so their right-answer counts, their share of cant_tell answers and their count of
   malformed replies are checked only as recorded, and three old files are not regraded at all.
   make reproduce says so in a note under each file, and this step prints every one of those
   notes in its summary and writes them into the step's text, never only the last line.
3. FHIR. The result of the last HL7 validator run, read from the committed
   results/fhir_validation.json (this step does not run the validator; make fhir-validate does),
   and the golden Bundles checked byte for byte against what the emitter produces today.
4. Web. The app builds, and the design gate passes: tokens, contrast and tap targets. The tap
   targets are measured on this build served on port 3100 (or WEB_PORT), or on a free port the
   script picks when something else holds it; it prints which, and checks the port is free again
   after.
   Two judge-checks in one checkout share apps/web/.next, so this step holds a lock on
   apps/web and the second one waits for the first to finish it.
5. Audit log. The hash chain walks from the genesis hash to the last entry with no break.
6. Secrets. gitleaks over the history when it is installed, and a scan of the working tree for
   anything shaped like a key.

Run: uv run python scripts/judge_check.py
     uv run python scripts/judge_check.py --quick   skip the web build, which is the slow one
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts import submit_check
from scripts.render_readme import summary_line

ROOT = Path(__file__).resolve().parents[1]
# Anything that looks like a live credential: the shapes submit-check and make secrets use, so a
# line such as EXPORT_TOKEN=... fails here too. The fake values in tests are all shorter than
# these, are placeholders the shapes leave out, or are named in .gitleaksignore.
KEY_SHAPES = tuple(submit_check.SECRET_PATTERNS.values())
SCAN_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".sh",
    ".env",
}
SCAN_SKIP = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "out",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".hypothesis",
    "ig-src",
    "uv.lock",
}


@dataclass
class Step:
    name: str
    ok: bool = True
    lines: list[str] = field(default_factory=list)
    seconds: float = 0.0
    # What the step's own tool says is not proved, printed under the step in the summary and kept
    # in the step's text: make reproduce's notes on numbers kept as recorded, and its skips.
    notes: list[str] = field(default_factory=list)

    def fail(self, line: str) -> None:
        self.ok = False
        self.lines.append(line)


# The dead proxy make demo-offline gives its processes: port 9 on this machine takes nothing, so a
# client that honours the proxy variables cannot reach another machine. Both spellings are set,
# because some clients read only one, and Python's urllib lets the lower case one win.
DEAD_PROXY = {
    "HTTP_PROXY": "http://127.0.0.1:9",
    "HTTPS_PROXY": "http://127.0.0.1:9",
    "NO_PROXY": "localhost,127.0.0.1",
}


def offline_env() -> dict[str, str]:
    """The environment every step runs in: no key, and a proxy that goes nowhere."""
    env = dict(os.environ)
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"):
        env.pop(name, None)
    for name, value in DEAD_PROXY.items():
        env[name] = value
        env[name.lower()] = value
    return env


def run(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
    proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)


def last_line(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "(no output)"


def step_tests(root: Path, env: dict[str, str]) -> Step:
    step = Step("tests")
    # No -q here: pyproject.toml already adds one, and a second hides the "N passed" line.
    rc, out = run(["uv", "run", "pytest"], root, env)
    if rc != 0:
        step.fail(f"pytest failed: {last_line(out)}")
    else:
        step.lines.append(f"python: {last_line(out)}")
    worker = root / "worker"
    if (worker / "package.json").exists():
        rc, out = run(["npm", "test", "--silent"], worker, env)
        passed = re.search(r"pass (\d+)", out)
        if rc != 0:
            step.fail(f"worker tests failed: {last_line(out)}")
        else:
            step.lines.append(f"worker: {passed.group(0) if passed else 'ok'}")
    return step


# make reproduce's line for one file (evals/reproduce.py, report): "ok   <path>: ...",
# "skip <path>: not regraded: <why>" or "FAIL <path>: ...", then any "       note: ..." lines.
REPRODUCE_FILE = re.compile(r"^(ok  |skip|FAIL) (\S+): (.*)$")


def joined(paths: list[str]) -> str:
    return paths[0] if len(paths) == 1 else f"{', '.join(paths[:-1])} and {paths[-1]}"


def reproduce_notes(out: str) -> list[str]:
    """Every note make reproduce prints under a file, and every file it skips, one line each.

    Its last line counts values and files and says "every one matches". Read alone, it hides that
    some numbers were never graded from a reply: the paid benchmark runs kept counts, not replies
    (judge walk 01, R02). A note printed under several files is said once, naming them all, in
    the order make reproduce printed them.
    """
    grouped: dict[str, list[str]] = {}
    path = ""
    for line in out.splitlines():
        m = REPRODUCE_FILE.match(line)
        if m:
            path = m.group(2)
            if m.group(1) == "skip":
                grouped.setdefault(m.group(3), []).append(path)
            continue
        text = line.strip()
        if text.startswith("note: ") and path:
            grouped.setdefault(text.removeprefix("note: "), []).append(path)
    return [f"note on {joined(paths)}: {text}" for text, paths in grouped.items()]


def step_reproduce(root: Path, env: dict[str, str]) -> Step:
    step = Step("reproduce")
    rc, out = run(["make", "--no-print-directory", "reproduce"], root, env)
    if rc != 0:
        failed = [ln.strip() for ln in out.splitlines() if ln.startswith("FAIL")]
        step.fail(f"make reproduce failed: {last_line(out)}")
        step.lines.extend(failed[:4])
    else:
        # Its notes are shown after this line, so it names them "below" (critic round 15 E02).
        step.lines.append(summary_line(step.name, last_line(out)))
    step.notes = reproduce_notes(out)
    return step


def files_validated(data: Mapping[str, Any]) -> int:
    """How many files the last validator run checked.

    scripts/fhir_validate.py writes files_validated as a number and files as the list of paths,
    so a missing count falls back to the length of the list.
    """
    count = data.get("files_validated")
    if isinstance(count, int):
        return count
    files = data.get("files") or []
    return len(files) if isinstance(files, list) else 0


def step_fhir(root: Path, env: dict[str, str]) -> Step:
    step = Step("fhir")
    results = root / "results" / "fhir_validation.json"
    if not results.exists():
        step.fail("results/fhir_validation.json is missing; run make fhir-validate")
        return step
    data = json.loads(results.read_text(encoding="utf-8"))
    errors = int(data.get("errors", 0) or 0)
    files = files_validated(data)
    commit = data.get("ig_commit", "?")
    if errors:
        step.fail(f"{errors} validation error(s) in the last run")
    # This step reads the committed results of the last validator run. It does not run the
    # validator, which needs Java and a download; make fhir-validate does that.
    step.lines.append(
        f"last validator run: {files} file(s) against hl7-eu/oah at {commit}, "
        f"{errors} errors, validator {data.get('validator_version', '?')}"
    )
    rc, out = run(
        ["uv", "run", "python", "-m", "pytest", "-q", "core/tests/test_fhir_emit.py"], root, env
    )
    if rc != 0:
        step.fail(f"the golden Bundles do not match the emitter: {last_line(out)}")
    return step


# The port the web app serves on unless WEB_PORT says otherwise (apps/web/scripts/web-port.mjs).
DEFAULT_WEB_PORT = 3100
# The web step's lock, inside apps/web/node_modules: one per checkout, ignored by git, and kept by
# next build, which empties .next.
WEB_LOCK = Path("node_modules") / ".judge-check-web.lock"


def port_free(port: int) -> bool:
    """True when nothing answers on 127.0.0.1:port and a server could bind it.

    SO_REUSEADDR, as Node sets it for a server: a port whose last connections are still closing
    counts as free, and one that another server listens on does not.
    """
    with socket.socket() as probe:
        probe.settimeout(1.0)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            return False
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def preferred_web_port() -> int:
    """WEB_PORT when it is set, as for every other web command, or else 3100."""
    raw = os.environ.get("WEB_PORT", "").strip()
    return int(raw) if raw.isdigit() and 0 < int(raw) < 65536 else DEFAULT_WEB_PORT


def pick_web_port(preferred: int | None = None) -> int:
    """The preferred port when it is free, or else one the system hands out (CRITIC_13 N01)."""
    preferred = preferred_web_port() if preferred is None else preferred
    if port_free(preferred):
        return preferred
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_port_free(port: int, seconds: float = 15.0) -> bool:
    deadline = time.monotonic() + seconds
    while not port_free(port):
        if time.monotonic() > deadline:
            return False
        time.sleep(0.25)
    return True


@contextmanager
def web_lock(web: Path) -> Iterator[None]:
    """Hold this checkout's web lock: one judge-check at a time builds and measures apps/web.

    Two judge-checks in one checkout share apps/web/.next and the files the build writes, so a
    second one waits here until the first has built, measured and stopped its server. The lock is
    the operating system's, so it goes when its process ends, however it ends.
    """
    path = web / WEB_LOCK
    with path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(
                "judge-check: another judge-check in this checkout is on its web step; "
                "waiting for it to finish",
                flush=True,
            )
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_stoppable(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
    """run(), but a judge-check that is stopped stops this child too, and so its web server."""
    proc = subprocess.Popen(
        argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        out, _ = proc.communicate()
    except BaseException:
        proc.terminate()
        proc.wait()
        raise
    return proc.returncode, out


def step_web(root: Path, env: dict[str, str], quick: bool) -> Step:
    step = Step("web")
    web = root / "apps" / "web"
    if quick:
        step.lines.append("skipped with --quick")
        return step
    if not (web / "node_modules").exists():
        step.fail("apps/web/node_modules is missing; run npm install in apps/web first")
        return step
    with web_lock(web):
        rc, out = run(["npm", "run", "build", "--silent"], web, env)
        if rc != 0:
            step.fail(f"the web build failed: {last_line(out)}")
            return step
        step.lines.append("next build ok")
        # Picked inside the lock, just before the design check starts its server on it.
        preferred = preferred_web_port()
        port = pick_web_port(preferred)
        busy = "" if port == preferred else f" ({preferred} is in use)"
        print(f"judge-check: the web step serves this build on port {port}{busy}", flush=True)
        rc, out = run_stoppable(
            ["node", "scripts/design-check.mjs"], web, {**env, "WEB_PORT": str(port)}
        )
        if rc != 0:
            step.fail(f"design-check failed: {last_line(out)}")
        else:
            step.lines.append(last_line(out))
        if wait_port_free(port):
            step.lines.append(f"served on port {port}{busy}, which is free again")
        else:
            step.fail(f"port {port} is still in use after the web step")
    return step


def step_audit(root: Path, env: dict[str, str]) -> Step:
    step = Step("audit log")
    log = root / "audit" / "log.jsonl"
    if not log.exists():
        step.lines.append("audit/log.jsonl does not exist on this branch yet")
        return step
    rc, out = run(["uv", "run", "python", "scripts/verify_audit.py"], root, env)
    if rc != 0:
        step.fail(f"the chain is broken: {last_line(out)}")
    else:
        step.lines.append(summary_line(step.name, last_line(out)))
    return step


def scan_tree(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SCAN_SKIP for part in path.parts):
            continue
        if path.suffix not in SCAN_SUFFIXES and path.name != ".env.example":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for shape in KEY_SHAPES:
            if shape.search(text):
                hits.append(str(path.relative_to(root)))
                break
    return hits


def step_secrets(root: Path, env: dict[str, str]) -> Step:
    step = Step("secrets")
    hits = scan_tree(root)
    if hits:
        step.fail(f"something shaped like a live key is in {', '.join(sorted(hits)[:4])}")
    else:
        step.lines.append("working tree: nothing shaped like a live key")
    if (root / ".env").exists():
        tracked = run(["git", "ls-files", "--error-unmatch", ".env"], root, env)[0] == 0
        if tracked:
            step.fail(".env is tracked by git")
        else:
            step.lines.append(".env exists here and is not tracked, as hard rule 14 asks")
    if shutil.which("gitleaks") and (root / ".git").exists():
        rc, out = run(
            ["gitleaks", "git", str(root), "--no-banner", "--redact", "--exit-code", "1"], root, env
        )
        if rc != 0:
            step.fail(f"gitleaks flagged the history: {last_line(out)}")
        else:
            step.lines.append("gitleaks: history clean")
    else:
        step.lines.append("gitleaks not installed here, so only the working tree was scanned")
    return step


def write_summary(out: Path, root: Path, steps: list[Step], last: str) -> None:
    """The summary the README shows (results/judge_check.json): one line per step, as printed,
    with the step's notes after its lines, so the README never shows a step without them."""
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True
    ).stdout.strip()
    doc = {
        "commit": commit,
        "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": [
            {
                "name": s.name,
                "ok": s.ok,
                "text": "; ".join(s.lines + s.notes),
                "seconds": round(s.seconds),
            }
            for s in steps
        ],
        "seconds": round(sum(s.seconds for s in steps)),
        "last": last,
    }
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="skip the web build")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument(
        "--out", type=Path, default=None, help="also write the summary to this JSON file"
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    env = offline_env()

    print(
        "judge-check: no API key in the environment, no network needed. This takes a few minutes."
    )
    steps: list[Step] = []
    for make in (
        lambda: step_tests(root, env),
        lambda: step_reproduce(root, env),
        lambda: step_fhir(root, env),
        lambda: step_web(root, env, args.quick),
        lambda: step_audit(root, env),
        lambda: step_secrets(root, env),
    ):
        started = time.monotonic()
        step = make()
        step.seconds = time.monotonic() - started
        steps.append(step)
        mark = "ok  " if step.ok else "FAIL"
        for line in step.lines + step.notes:
            print(f"  {mark} {step.name}: {line}")

    print()
    failed = [s for s in steps if not s.ok]
    for step in steps:
        mark = "PASS" if step.ok else "FAIL"
        headline = step.lines[0] if step.lines else ""
        print(f"{mark}  {step.name:<10} {step.seconds:5.1f}s  {headline}")
        # The notes stay in the summary: a PASS line alone would read as "every number regraded".
        for note in step.notes:
            print(f"{'':25}{note}")
    last = (
        f"judge-check: {len(failed)} of {len(steps)} steps failed"
        if failed
        else f"judge-check: {len(steps)} of {len(steps)} steps passed, offline, with no key"
    )
    if args.out:
        write_summary(args.out, root, steps, last)
    print(last)
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
