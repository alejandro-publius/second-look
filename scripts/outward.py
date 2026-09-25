"""The one door every Mac job goes through to reach anything outside this machine (UPDATE_30).

A push, a deploy, a comment on the status issue, a notification, a web request or a name lookup
is a method of Outward and nothing else. The jobs (scripts/lock_analysis.py, scripts/uptime.py,
scripts/sandbox_retry.py, scripts/hl7_watch.py, scripts/rollback.py, scripts/panel_status.py)
take an Outward as an argument, so a test hands them a stand-in that records each call and answers
as the test says, and nothing leaves the machine. Commands that only touch this checkout (git
commit, make check) are not outward and do not come through here.

The status issue is issue 4 of this repository: the lead's channel with Alex until the submission.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = "alejandro-publius/second-look"
STATUS_ISSUE = 4
USER_AGENT = "second-look-mac-job (+https://github.com/alejandro-publius/second-look)"


@dataclass
class Done:
    """What a command gave back."""

    code: int
    out: str = ""
    err: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 0

    def tail(self, lines: int = 3) -> str:
        """The last few lines of what it printed, for a log line."""
        text = (self.err.strip() or self.out.strip()).splitlines()
        return " / ".join(text[-lines:])[:400]


@dataclass
class Reply:
    """What a web request gave back: a status (0 when nothing answered) and the body."""

    status: int
    text: str = ""
    error: str = ""

    def json(self) -> object:
        return json.loads(self.text)


class Outward:
    """The real thing. Every method here reaches past this machine."""

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        stdin: str | None = None,
        timeout: float = 1800,
    ) -> Done:
        """A command that talks to the network: git fetch and push, wrangler, gh, a live check."""
        full_env = {**os.environ, **(env or {})}
        try:
            proc = subprocess.run(
                list(argv),
                cwd=cwd,
                env=full_env,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return Done(127, "", f"{argv[0]}: {e}")
        return Done(proc.returncode, proc.stdout, proc.stderr)

    def http(
        self,
        url: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 20,
    ) -> Reply:
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("User-Agent", USER_AGENT)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return Reply(r.status, r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return Reply(e.code, e.read().decode("utf-8", "replace"), f"HTTP {e.code}")
        except (OSError, ValueError) as e:
            return Reply(0, "", str(e).splitlines()[0][:200] if str(e) else type(e).__name__)

    def get(self, url: str, *, timeout: float = 20) -> Reply:
        return self.http(url, timeout=timeout)

    def resolves(self, host: str) -> bool:
        """Whether the name has an address. Nothing is sent to the host itself."""
        try:
            return bool(socket.getaddrinfo(host, 443))
        except OSError:
            return False

    def comment(self, text: str) -> Done:
        """One comment on the status issue."""
        return self.run(
            ["gh", "issue", "comment", str(STATUS_ISSUE), "--repo", REPO, "--body-file", "-"],
            stdin=text,
            timeout=120,
        )

    def issue_body(self) -> str | None:
        done = self.run(
            ["gh", "issue", "view", str(STATUS_ISSUE), "--repo", REPO, "--json", "body"],
            timeout=120,
        )
        if not done.ok:
            return None
        try:
            return str(json.loads(done.out)["body"])
        except (ValueError, KeyError, TypeError):
            return None

    def set_issue_body(self, body: str) -> Done:
        return self.run(
            ["gh", "issue", "edit", str(STATUS_ISSUE), "--repo", REPO, "--body-file", "-"],
            stdin=body,
            timeout=120,
        )

    def notify(self, title: str, text: str) -> Done:
        """A macOS notification on this Mac's screen."""

        def quoted(s: str) -> str:
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

        script = f"display notification {quoted(text)} with title {quoted(title)}"
        return self.run(["osascript", "-e", script], timeout=30)
