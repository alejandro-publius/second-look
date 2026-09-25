"""judge-check's web step when port 3100 is busy, and two judge-checks in one checkout at once.

CRITIC_13 N01: make judge-check reported a false tap target failure whenever something else
served port 3100 (make dev, make demo-offline, another session), because the design check took any
answer on 3100 for the build it had just started. UPDATE_30 section 1 item 5: the web port comes
from WEB_PORT (3100 by default), judge-check serves on a free port and says which, the design
check refuses a port that something else holds, and a lock lets two judge-checks share apps/web.

The last test runs the real web step (a next build and the design check, about two minutes) with
port 3100 taken first. It runs only with JUDGE_CHECK_WEB=1, because judge-check itself runs this
suite and would build the web app twice.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from scripts import judge_check

ROOT = judge_check.ROOT
WEB = ROOT / "apps" / "web"


class OldBuild(BaseHTTPRequestHandler):
    """Somebody else's server: answers every page with 200 and counts what it was asked."""

    asked: list[str] = []

    def do_GET(self) -> None:
        OldBuild.asked.append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OLD BUILD")

    def log_message(self, *args: object) -> None:
        pass


def serve_on(port: int) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), OldBuild)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def busy_port() -> Iterator[int]:
    """A port another server already answers on, with a 200 for every page."""
    OldBuild.asked = []
    server = serve_on(0)
    try:
        yield int(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()


def test_a_port_with_a_server_on_it_is_not_free(busy_port: int) -> None:
    assert not judge_check.port_free(busy_port)
    assert judge_check.port_free(free_port())


def test_the_preferred_port_is_taken_when_it_is_free(monkeypatch: pytest.MonkeyPatch) -> None:
    port = free_port()
    monkeypatch.setenv("WEB_PORT", str(port))
    assert judge_check.preferred_web_port() == port
    assert judge_check.pick_web_port() == port


def test_without_web_port_the_preferred_port_is_3100(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEB_PORT", raising=False)
    assert judge_check.preferred_web_port() == 3100
    monkeypatch.setenv("WEB_PORT", "not a port")
    assert judge_check.preferred_web_port() == 3100


def test_a_busy_preferred_port_moves_the_web_step_to_a_free_one(busy_port: int) -> None:
    picked = judge_check.pick_web_port(busy_port)
    assert picked != busy_port
    assert judge_check.port_free(picked)


def fake_build(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A checkout whose build passes at once, so only the port and the lock are tested."""
    (tmp_path / "apps" / "web" / "node_modules").mkdir(parents=True)
    monkeypatch.setattr(judge_check, "run", lambda argv, cwd, env: (0, "built"))
    return tmp_path


def test_the_web_step_serves_on_a_free_port_says_which_and_frees_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    busy_port: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = fake_build(monkeypatch, tmp_path)
    monkeypatch.setenv("WEB_PORT", str(busy_port))
    seen: dict[str, str] = {}

    def design_check(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
        # Stands in for the design check: its server takes the port it was given, then stops.
        seen["port"] = env["WEB_PORT"]
        server = serve_on(int(env["WEB_PORT"]))
        server.shutdown()
        server.server_close()
        return 0, "design-check: clean. tap targets 3 passed."

    monkeypatch.setattr(judge_check, "run_stoppable", design_check)
    step = judge_check.step_web(root, {}, quick=False)
    assert step.ok, step.lines
    port = int(seen["port"])
    assert port != busy_port
    assert step.lines == [
        "next build ok",
        "design-check: clean. tap targets 3 passed.",
        f"served on port {port} ({busy_port} is in use), which is free again",
    ]
    assert f"serves this build on port {port} ({busy_port} is in use)" in capsys.readouterr().out
    # Nothing asked the other server for a page.
    assert OldBuild.asked == []


def test_a_port_left_in_use_after_the_design_check_fails_the_step(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = fake_build(monkeypatch, tmp_path)
    monkeypatch.setenv("WEB_PORT", str(free_port()))
    left: list[HTTPServer] = []

    def design_check(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
        left.append(serve_on(int(env["WEB_PORT"])))
        return 0, "design-check: clean."

    monkeypatch.setattr(judge_check, "run_stoppable", design_check)
    original = judge_check.wait_port_free
    monkeypatch.setattr(judge_check, "wait_port_free", lambda port: original(port, 0.5))
    try:
        step = judge_check.step_web(root, {}, quick=False)
    finally:
        for server in left:
            server.shutdown()
            server.server_close()
    assert not step.ok
    assert step.lines[-1].endswith("is still in use after the design check stopped its server")


def test_two_web_steps_in_one_checkout_take_turns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    web = tmp_path / "apps" / "web"
    (web / "node_modules").mkdir(parents=True)
    spans: list[tuple[str, float, float]] = []
    first_in = threading.Event()

    def hold(name: str, seconds: float) -> None:
        with judge_check.web_lock(web):
            start = time.monotonic()
            first_in.set()
            time.sleep(seconds)
            spans.append((name, start, time.monotonic()))

    first = threading.Thread(target=hold, args=("first", 0.6))
    first.start()
    assert first_in.wait(5)
    second = threading.Thread(target=hold, args=("second", 0.0))
    second.start()
    first.join(10)
    second.join(10)
    by_name = {name: (start, end) for name, start, end in spans}
    assert by_name["second"][0] >= by_name["first"][1], spans
    assert "another judge-check in this checkout is on its web step" in capsys.readouterr().out
    # The lock file lives where git does not look and next build does not empty.
    assert (web / judge_check.WEB_LOCK).exists()
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(WEB / judge_check.WEB_LOCK)], cwd=ROOT, check=False
    )
    assert ignored.returncode == 0


def design_check(port: int) -> subprocess.CompletedProcess[str]:
    if shutil.which("node") is None or not (WEB / "node_modules").exists():
        pytest.skip("needs node and npm ci in apps/web")
    env = {**os.environ, "WEB_PORT": str(port)}
    env.pop("SKIP_TAP", None)
    return subprocess.run(
        ["node", "scripts/design-check.mjs"],
        cwd=WEB,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def test_the_design_check_refuses_a_port_another_server_holds(busy_port: int) -> None:
    # The critic's reproduction: another server on the port answered 200, the design check took it
    # for its own build and measured it, and failed on tap targets.
    proc = design_check(busy_port)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1, out
    assert f"port {busy_port} is in use by another process" in out, out
    assert "tap target measurement failed" not in out, out
    assert OldBuild.asked == [], "the design check asked the other server for a page"


@pytest.mark.skipif(
    os.environ.get("JUDGE_CHECK_WEB") != "1",
    reason="builds the web app for real, about two minutes: set JUDGE_CHECK_WEB=1",
)
def test_with_3100_taken_first_the_real_web_step_still_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WEB_PORT", raising=False)
    OldBuild.asked = []
    server = None
    if judge_check.port_free(3100):
        server = serve_on(3100)
    try:
        assert not judge_check.port_free(3100)
        step = judge_check.step_web(ROOT, judge_check.offline_env(), quick=False)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
    assert step.ok, step.lines
    served = step.lines[-1]
    assert served.startswith("served on port ") and "(3100 is in use)" in served, step.lines
    assert "served on port 3100 " not in served
    assert step.lines[1].startswith("design-check: clean."), step.lines
    assert OldBuild.asked == [], "the web step asked the server on 3100 for a page"
