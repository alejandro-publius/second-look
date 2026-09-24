"""apps/web/playwright.config.ts, run for real on small specs, with no browser and not on 3100.

REVIEW_03 R50: CI retried each web test once, so a test that failed and then passed counted as
green. R55: the config reused whatever already answered on its port, so make e2e could test
somebody else's build. Each test here loads the real config and changes only what it must: the
folder of specs, the reporter and, for the server, a free port in place of 3100, so these runs
never get in the way of a server another session keeps on 3100.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "web"
CONFIG = WEB / "playwright.config.ts"
PACKAGE = WEB / "node_modules" / "@playwright" / "test"


def playwright(
    tmp_path: Path, spec: str, overrides: str, ci: bool, reuse: bool = False
) -> tuple[int, str]:
    """Run the real config, with overrides, on one spec in tmp_path. Exit code and output."""
    if shutil.which("node") is None or not (PACKAGE / "cli.js").exists():
        pytest.skip("needs node and npm ci in apps/web")
    (tmp_path / "specs").mkdir()
    imports = f"import {{ test, expect }} from {json.dumps(str(PACKAGE / 'index.mjs'))};\n"
    (tmp_path / "specs" / "one.spec.ts").write_text(imports + spec, encoding="utf-8")
    (tmp_path / "pw.config.ts").write_text(
        f"import base from {json.dumps(str(CONFIG))};\n"
        "export default {\n"
        "  ...base,\n"
        '  testDir: "./specs",\n'
        '  outputDir: "./results",\n'
        '  reporter: [["list"]],\n'
        f"  {overrides}\n"
        "};\n",
        encoding="utf-8",
    )
    drop = ("CI", "PW_REUSE")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PLAYWRIGHT_") and k not in drop}
    if ci:
        env["CI"] = "1"
    if reuse:
        env["PW_REUSE"] = "1"
    proc = subprocess.run(
        ["node", str(PACKAGE / "cli.js"), "test", "-c", str(tmp_path / "pw.config.ts")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


FAILS_ONCE = """
test("fails on its first try only", async ({}, info) => {
  expect(info.retry).toBe(1);
});
"""


def test_in_ci_a_test_that_passes_only_on_its_retry_fails_the_run(tmp_path: Path) -> None:
    code, out = playwright(tmp_path, FAILS_ONCE, "webServer: undefined,", ci=True)
    assert "1 flaky" in out, out
    assert code != 0, out


def test_outside_ci_there_is_no_retry(tmp_path: Path) -> None:
    code, out = playwright(tmp_path, FAILS_ONCE, "webServer: undefined,", ci=False)
    assert "1 failed" in out, out
    assert code != 0, out


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def old_build() -> Iterator[int]:
    """Somebody else's server, already answering on a port before the run starts."""

    class Old(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OLD BUILD")

        def log_message(self, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", free_port()), Old)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield int(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()


SERVES_THIS_BUILD = """
test("the page is this build", async ({ request }) => {
  expect(await (await request.get("/")).text()).toBe("NEW BUILD");
});
"""


def own_server(port: int) -> str:
    """The config's webServer and baseURL, moved to port, starting a server that says NEW BUILD."""
    serve = (
        f"require('http').createServer((q, s) => s.end('NEW BUILD')).listen({port}, '127.0.0.1')"
    )
    url = f"http://127.0.0.1:{port}"
    return (
        f"webServer: {{ ...base.webServer, command: {json.dumps(f'node -e "{serve}"')}, "
        f"url: {json.dumps(url + '/')}, timeout: 60000 }},\n"
        f"  use: {{ ...base.use, baseURL: {json.dumps(url)} }},"
    )


def test_a_server_already_on_the_port_is_refused_not_tested(tmp_path: Path, old_build: int) -> None:
    code, out = playwright(tmp_path, SERVES_THIS_BUILD, own_server(old_build), ci=False)
    assert "is already used" in out, out
    assert code != 0, out


def test_a_server_already_on_the_port_is_refused_in_ci_too(tmp_path: Path, old_build: int) -> None:
    code, out = playwright(tmp_path, SERVES_THIS_BUILD, own_server(old_build), ci=True)
    assert "is already used" in out, out
    assert code != 0, out


def test_on_a_free_port_the_config_starts_its_own_server(tmp_path: Path) -> None:
    code, out = playwright(tmp_path, SERVES_THIS_BUILD, own_server(free_port()), ci=False)
    assert "1 passed" in out, out
    assert code == 0, out


def test_design_check_alone_may_reuse_the_build_it_started(tmp_path: Path, old_build: int) -> None:
    # scripts/design-check.mjs starts this build on 3100 and then runs design.spec.ts with
    # PW_REUSE=1; the server here stands in for the one it started.
    spec = SERVES_THIS_BUILD.replace('toBe("NEW BUILD")', 'toBe("OLD BUILD")')
    code, out = playwright(tmp_path, spec, own_server(old_build), ci=False, reuse=True)
    assert "1 passed" in out, out
    assert code == 0, out
    design_check = (WEB / "scripts" / "design-check.mjs").read_text(encoding="utf-8")
    assert 'PW_REUSE: "1"' in design_check
