"""A stand-in for scripts/outward.py's Outward: it records every call and answers as told.

Nothing it does leaves the machine. `answers` maps the start of a command (a tuple of its first
words) to what it gives back, the first match winning; `pages` maps a URL to a Reply. A test
reads `calls`, `comments` and `notes` afterwards.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from scripts.outward import Done, Outward, Reply

Answer = Done | Callable[[list[str], Path | None, Mapping[str, str] | None], Done]


class FakeOutward(Outward):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.cwds: list[Path | None] = []
        self.envs: list[dict[str, str]] = []
        self.answers: list[tuple[tuple[str, ...], Answer]] = []
        self.pages: dict[str, Reply] = {}
        self.fetched: list[tuple[str, str]] = []
        self.comments: list[str] = []
        self.notes: list[tuple[str, str]] = []
        self.hosts: dict[str, bool] = {}
        self.issue: str | None = "The top paragraph: Alex's items with dates.\n\nMore below."
        self.issue_edits: list[str] = []

    def answer(self, prefix: Sequence[str], result: Answer) -> None:
        self.answers.insert(0, (tuple(prefix), result))

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        stdin: str | None = None,
        timeout: float = 1800,
    ) -> Done:
        args = list(argv)
        self.calls.append(args)
        self.cwds.append(cwd)
        self.envs.append(dict(env or {}))
        for prefix, result in self.answers:
            if tuple(args[: len(prefix)]) == prefix:
                return result(args, cwd, env) if callable(result) else result
        return Done(0, "", "")

    def http(
        self,
        url: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 20,
    ) -> Reply:
        self.fetched.append((method, url))
        return self.pages.get(f"{method} {url}", self.pages.get(url, Reply(0, "", "no answer")))

    def resolves(self, host: str) -> bool:
        self.calls.append(["resolve", host])
        self.cwds.append(None)
        self.envs.append({})
        return self.hosts.get(host, False)

    def comment(self, text: str) -> Done:
        self.comments.append(text)
        return Done(0)

    def issue_body(self) -> str | None:
        return self.issue

    def set_issue_body(self, body: str) -> Done:
        self.issue_edits.append(body)
        self.issue = body
        return Done(0)

    def notify(self, title: str, text: str) -> Done:
        self.notes.append((title, text))
        return Done(0)

    def ran(self, *prefix: str) -> list[list[str]]:
        """Every recorded command that starts with these words."""
        return [c for c in self.calls if tuple(c[: len(prefix)]) == prefix]
