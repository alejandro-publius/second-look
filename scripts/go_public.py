"""Make the repository public on Sep 30, in the one safe order (UPDATE_30 section 8).

    make go-public            says what it would do and changes nothing
    make go-public GO=dry     runs every step before the flip in a throwaway copy, then stops
    make go-public GO=yes     does it all, on main: Alex, or any Claude Code window on the Mac

The steps, in order. Each prints one line: PASS, FAIL or SKIP, its name, and what it saw. GO=yes
stops at the first FAIL. GO=dry runs every step before the flip even after a FAIL, so one run
shows every gap, and it runs them in a throwaway git worktree, so main is never touched.

  start      on main with a clean tree, not behind origin/main. Fetches every branch, tag and
             pull request head GitHub holds, because every one of them turns public.
  secrets    gitleaks over every commit of those and HEAD, then the repo's own scan of the tree.
  notes      git rm -r docs/internal, every mention in a tracked file reworded, in one commit.
             SKIP when the tip has no docs/internal. The files in READERS keep the path, and
             each copes once the folder is gone.
  tests      make lint and the Python tests, on the tree without the notes.
  submit     make submit-check fails on nothing but the repo not being public yet.
  readme     the README rendered by GitHub (here, when gh cannot read the repo); every image
             and every link answers.
  changelog  CHANGELOG.md's v1.0 section names every day with commits, up to yesterday.
  ------     GO=dry (--no-flip) stops here, before anything leaves this Mac.
  push       git push origin main.
  flip       gh repo edit --visibility public. SKIP when it already is.
  public     logged out (curl, no token, no cookie): the README page, its images, the CI badge
             and the live link all load.
  tag        v1.0 on the tip, pushed. SKIP when it is there.
  release    the GitHub release v1.0, its notes from CHANGELOG.md. SKIP when it is there.

Every step before the flip is safe to run again: a second run finds the notes commit made and
skips it. The notes leave the tip only. Git history still holds docs/internal, and this script
never rewrites history (hard rule 15).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
INTERNAL = "docs/internal"
# The folder's own README is tracked, so when it is gone the folder is gone from git, even if a
# file nobody committed is still on this disk.
NOTES_MARKER = f"{INTERNAL}/README.md"
GITLEAKS_CONFIG = ".gitleaks.toml"
REPO_SLUG = "alejandro-publius/second-look"
PACIFIC = ZoneInfo("America/Los_Angeles")
TAG = "v1.0"
RELEASE_TITLE = "Second Look v1.0"
CHANGELOG = "CHANGELOG.md"
FIRST_DAY = date(2026, 9, 16)  # the hackathon's first day

# Code that reads or writes the folder, and how each copes once go-public has removed it. These
# keep the path as it is: rewording a path that code opens would break the code.
READERS = {
    "scripts/done_check.py": "reads DONE.md there; once DONE.md is gone it says so and exits 0",
    "scripts/done_items.py": "the checks behind DONE.md; only done_check runs them, and it runs "
    "none once DONE.md is gone",
    "scripts/tests/test_done_check.py": "its three tests of the real checklist skip once DONE.md "
    "is gone",
    "scripts/tests/test_done_items.py": "builds the folder in its own temporary trees; its one "
    "test of the real panel study skips once that file is gone",
    "scripts/harden_links.py": "writes its page there while the notes exist, and only "
    "results/harden/links.json once they are gone",
    "scripts/harden_axe.py": "writes its page there while the notes exist, and only "
    "results/harden/axe.json once they are gone",
}
# The files that keep the path: the readers, this script and its tests, and the gitleaks
# allowlist, because gitleaks reads the history, which keeps the folder and its patch files.
KEEP = {"scripts/go_public.py", "scripts/tests/test_go_public.py", GITLEAKS_CONFIG, *READERS}

# The one line in the README that talks about the folder itself goes, rather than being reworded.
README_LINE = re.compile(r"; docs/internal/ holds the working notes, removed before the repo opens")
# A mention ends at a space, a stop, a bracket or a double quote; the quote covers JSON strings
# in results/, such as the link check's targets.
MENTION = re.compile(
    r"`?docs/internal(?:/(?:(?:updates|reports|reviews|upstream)/)?(?P<name>[A-Za-z0-9_.-]+?)?(?:\.md)?/?)?`?"
    r"(?=[\s,.;:)\"]|$)"
)
ALLOWED_SUBMIT_FAILURES = {"repo_public"}
SUBMIT_SUMMARY = re.compile(r"^submit-check: (\d+) failed: (.*)$", re.MULTILINE)
COMMIT_MESSAGE = "Open the repository: remove the working notes from the tip; history keeps them"
# Every commit that turns public: each branch, tag and pull request head GitHub holds (fetched
# by the start step), and HEAD, which holds the notes commit before it is pushed.
GITLEAKS_LOG_OPTS = "--full-history --remotes=origin --tags HEAD"
FETCH = [
    "git",
    "fetch",
    "--quiet",
    "--tags",
    "origin",
    "+refs/heads/*:refs/remotes/origin/*",
    "+refs/pull/*/head:refs/remotes/origin/pull/*",
]
CHANGELOG_DAY = re.compile(
    r"^### (?:[A-Z][a-z]{2} )?(?P<month>Sep|Oct) (?P<day>\d{1,2})"
    r"(?: to (?:[A-Z][a-z]{2} )?(?:(?P<month2>Sep|Oct) )?(?P<day2>\d{1,2}))?\s*$",
    re.M,
)
MONTHS = {"Sep": 9, "Oct": 10}
BADGE = re.compile(r"^https://github\.com/(?P<slug>[^/]+/[^/]+)/actions/workflows/[^/]+/badge\.svg")


def public_cmd(slug: str = REPO_SLUG) -> list[str]:
    return [
        "gh",
        "repo",
        "edit",
        slug,
        "--visibility",
        "public",
        "--accept-visibility-change-consequences",
    ]


PUBLIC_CMD = public_cmd()


# ---------------------------------------------------------------------------------------------
# Commands. Every outward call goes through run_parts, which the tests replace.


def run_parts(
    cmd: list[str], cwd: Path = ROOT, env: Mapping[str, str] | None = None
) -> tuple[int, str, str]:
    """The exit code, stdout and stderr, kept apart."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, env=dict(env) if env else None
        )
    except OSError as e:
        return 127, "", f"could not run {cmd[0]}: {e}"
    return proc.returncode, proc.stdout, proc.stderr


def run(cmd: list[str], cwd: Path = ROOT, env: Mapping[str, str] | None = None) -> tuple[int, str]:
    code, out, err = run_parts(cmd, cwd, env)
    return code, (out + err).strip()


def one_line(text: str, limit: int = 400) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


def last_line(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "(no output)"


def said(out: str, err: str) -> str:
    """What a command said last: its own output, not uv's notes on stderr about installing."""
    return last_line(out) if out.strip() else last_line(err)


def counted(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}{'es' if word.endswith('ch') else 's'}"


@dataclass
class Step:
    name: str
    result: str  # PASS, FAIL or SKIP
    output: str

    @property
    def failed(self) -> bool:
        return self.result == "FAIL"

    def line(self) -> str:
        return f"{self.result:4}  {self.name:9}  {one_line(self.output)}"


def passed(name: str, output: str) -> Step:
    return Step(name, "PASS", one_line(output))


def failed(name: str, output: str) -> Step:
    return Step(name, "FAIL", one_line(output))


def skipped(name: str, output: str) -> Step:
    return Step(name, "SKIP", one_line(output))


@dataclass
class Run:
    """What the steps share: where they work, which repo, and what the readme step found."""

    root: Path
    slug: str = REPO_SLUG
    dry: bool = False
    today: date = field(default_factory=lambda: datetime.now(PACIFIC).date())
    sleep: Callable[[float], None] = time.sleep
    attempts: int = 6
    wait: float = 10.0
    images: list[str] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------------------------
# The working notes


def rewrite(text: str) -> str:
    """Every mention of the folder becomes a plain phrase that points nowhere."""
    text = README_LINE.sub("", text)

    def named(m: re.Match[str]) -> str:
        name = (m.group("name") or "").replace("_", " ").strip()
        return f"the team's working notes ({name})" if name else "the team's working notes"

    return MENTION.sub(named, text)


def mentions(root: Path = ROOT) -> list[tuple[str, int]]:
    """Each tracked file outside the folder that names it, and how often, except those in KEEP."""
    excluded = [f":!{INTERNAL}", *(f":!{path}" for path in sorted(KEEP))]
    code, out = run(["git", "grep", "-c", INTERNAL, "--", ".", *excluded], root)
    rows = []
    for line in out.splitlines() if code == 0 else []:
        path, _, count = line.rpartition(":")
        rows.append((path, int(count)))
    return rows


def notes_gone(path: Path, root: Path = ROOT) -> bool:
    """True when path lies in the working notes and go-public has removed them: a script that
    writes a page there then writes nothing, rather than making the folder again."""
    folder = (root / INTERNAL).resolve()
    inside = path.resolve() == folder or folder in path.resolve().parents
    return inside and not (root / NOTES_MARKER).is_file()


# ---------------------------------------------------------------------------------------------
# submit-check's summary


def submit_failures(output: str) -> set[str] | None:
    """The names on the last "submit-check: N failed: ..." line anywhere in the output.

    None when there is no such line, or when its count and its names disagree: submit-check
    crashed or was cut off, so nothing it says can be trusted. Make adds its own lines after it
    ("make: *** [submit-check] Error 1"), which is why this does not read only the last line.
    """
    found = SUBMIT_SUMMARY.findall(output)
    if not found:
        return None
    count, listed = found[-1]
    if int(count) == 0:
        return set()
    names = {n.strip() for n in listed.split(",") if n.strip()}
    return names if len(names) == int(count) else None


def submit_blocker(code: int, stdout: str) -> str | None:
    """Why the run must stop after make submit-check, or None when it may publish."""
    failed_checks = submit_failures(stdout)
    if failed_checks is None:
        return "submit-check printed no summary line it could read (did it crash?)"
    others = failed_checks - ALLOWED_SUBMIT_FAILURES
    if others:
        return f"submit-check failed on {sorted(others)}"
    if code != 0 and not failed_checks:
        return f"submit-check exited {code} but named no failed check"
    return None


# ---------------------------------------------------------------------------------------------
# The changelog


def release_notes(text: str) -> str:
    """The v1.0 section of CHANGELOG.md, without its heading: the tag's and the release's notes."""
    m = re.search(rf"^## {re.escape(TAG)}\b.*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end() :]
    end = re.search(r"^## ", rest, re.M)
    return rest[: end.start() if end else len(rest)].strip()


def days_named(notes: str, year: int = FIRST_DAY.year) -> set[date]:
    """Every day a "### Sep 20" or "### Sep 16 to 19" heading covers."""
    days: set[date] = set()
    for m in CHANGELOG_DAY.finditer(notes):
        start = date(year, MONTHS[m["month"]], int(m["day"]))
        end = start
        if m["day2"]:
            end = date(year, MONTHS[m["month2"] or m["month"]], int(m["day2"]))
        while start <= end:
            days.add(start)
            start += timedelta(days=1)
    return days


def commit_days(root: Path) -> set[date] | None:
    """The Pacific days on which HEAD's history has commits, or None when git log fails."""
    env = {**os.environ, "TZ": "America/Los_Angeles"}
    code, out, _err = run_parts(
        ["git", "log", "--format=%cd", "--date=format-local:%Y-%m-%d", "HEAD"], root, env
    )
    if code != 0:
        return None
    return {date.fromisoformat(d) for d in out.split()}


# ---------------------------------------------------------------------------------------------
# The README


class _Refs(HTMLParser):
    """Every image and link in rendered HTML, and every id a link may point at."""

    def __init__(self) -> None:
        super().__init__()
        self.images: list[str] = []
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "img" and a.get("src"):
            self.images.append(a.get("data-canonical-src") or a["src"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        for key in ("id", "name"):
            if a.get(key):
                self.ids.add(a[key].removeprefix("user-content-"))


def render_readme(run_: Run) -> tuple[str, str]:
    """The README as HTML and who rendered it: GitHub, when gh can read the repository."""
    text = (run_.root / "README.md").read_text(encoding="utf-8")
    code, _ = run(["gh", "repo", "view", run_.slug, "--json", "name"], run_.root)
    if code == 0:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "readme.json"
            body.write_text(
                json.dumps({"text": text, "mode": "gfm", "context": run_.slug}), encoding="utf-8"
            )
            code, html, _err = run_parts(["gh", "api", "markdown", "--input", str(body)], run_.root)
        if code == 0 and html.strip():
            return html, "GitHub"
    return local_html(text), "the local renderer"


def local_html(text: str) -> str:
    """Markdown as GitHub renders it, near enough to find every image and link: tables, raw
    HTML, and bare addresses made into links, as GitHub makes them."""
    from markdown_it import MarkdownIt

    return MarkdownIt("commonmark", {"linkify": True}).enable(["table", "linkify"]).render(text)


def tracked(root: Path) -> set[str]:
    """Every tracked file and every folder that holds one."""
    code, out = run(["git", "ls-files", "-z"], root)
    files = {p for p in out.split("\0") if p} if code == 0 else set()
    folders = {str(parent) for p in files for parent in Path(p).parents if str(parent) != "."}
    return files | folders


LinkResult = tuple[str, str]  # (status, detail): ok, private, skipped, blocked or dead


def check_links(urls: list[str]) -> dict[str, LinkResult]:
    """One GET per address, as the link check does it: the hosts hard rules 9 and 10 name are
    skipped or paced, our own repository is looked up in git while it is private."""
    from scripts.harden_links import check_urls

    results = asyncio.run(check_urls(urls))
    return {url: (r.status, r.detail) for url, r in results.items()}


def readme_problems(run_: Run, html: str) -> tuple[list[str], list[str], int, int]:
    """Dead images and links, the addresses listed as blocked, and how many of each were read."""
    from scripts.harden_links import anchors_of

    refs = _Refs()
    refs.feed(html)
    images = list(dict.fromkeys(refs.images))
    links = [u for u in dict.fromkeys(refs.links) if u not in images]
    run_.images = images
    known = tracked(run_.root)
    readme = run_.root / "README.md"
    anchors = anchors_of(readme) | refs.ids
    dead: list[str] = []
    external: list[str] = []
    for target in [*images, *links]:
        if target.startswith(("mailto:", "tel:")):
            continue
        if re.match(r"https?://", target):
            external.append(target)
            continue
        path, _, anchor = target.partition("#")
        path = unquote(path.split("?")[0]).strip("/")
        path = os.path.normpath(path) if path else ""
        if not path:
            if anchor and anchor.lower() not in anchors:
                dead.append(f"#{anchor}: no such heading in README.md")
            continue
        if path not in known:
            dead.append(f"{target}: not a tracked file")
        elif anchor and path.endswith(".md"):
            if anchor.lower() not in anchors_of(run_.root / path):
                dead.append(f"{target}: no such heading in {path}")
    results = check_links(external) if external else {}
    blocked = []
    for url in external:
        status, detail = results.get(url, ("dead", "not checked"))
        if status == "dead":
            dead.append(f"{url}: {detail}")
        elif status == "blocked":
            blocked.append(f"{url} ({detail})")
    return dead, blocked, len(images), len(links)


def ci_badge(images: list[str], slug: str) -> str | None:
    return next((u for u in images if (m := BADGE.match(u)) and m["slug"] == slug), None)


def live_link(root: Path) -> str | None:
    from scripts.submit_check import LIVE_FIELD, URL_RE, devpost_sections, field_text

    text = (root / "docs" / "devpost.md").read_text(encoding="utf-8")
    link = (field_text(devpost_sections(text).get(LIVE_FIELD, "")) or "").strip()
    return link if URL_RE.fullmatch(link) else None


# ---------------------------------------------------------------------------------------------
# The steps before the flip


def step_start(root: Path, dry: bool) -> Step:
    _, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
    _, status = run(["git", "status", "--porcelain"], root)
    code, out = run(FETCH, root)
    if code != 0:
        return failed("start", f"git fetch from origin failed: {last_line(out)}")
    _, refs = run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/remotes/origin", "refs/tags"], root
    )
    names = refs.split()
    pulls = sum(1 for r in names if r.startswith("refs/remotes/origin/pull/"))
    tags = sum(1 for r in names if r.startswith("refs/tags/"))
    branches = len(names) - pulls - tags - names.count("refs/remotes/origin/HEAD")
    code, behind = run(["git", "rev-list", "--count", "HEAD..origin/main"], root)
    behind = behind if code == 0 else "?"
    _, sha = run(["git", "rev-parse", "--short", "HEAD"], root)
    seen = (
        f"on {branch} at {sha}, {'a clean tree' if not status else 'uncommitted changes'}, "
        f"{behind} behind origin/main; fetched {counted(branches, 'branch')}, "
        f"{counted(tags, 'tag')} and {counted(pulls, 'pull request head')}"
    )
    if dry:
        return passed("start", seen + "; the dry run reads HEAD in a throwaway worktree")
    if branch != "main":
        return failed("start", f"refused: this is {branch}, not main")
    if status:
        return failed("start", "refused: the tree is not clean: " + status)
    if behind != "0":
        return failed("start", f"refused: {behind} commits behind origin/main; pull first")
    return passed("start", seen)


def step_secrets(run_: Run) -> Step:
    if not shutil.which("gitleaks"):
        return failed("secrets", "gitleaks is not installed; brew install gitleaks")
    code, out = run(
        [
            "gitleaks",
            "git",
            ".",
            f"--log-opts={GITLEAKS_LOG_OPTS}",
            "--redact",
            "--no-banner",
            "--exit-code",
            "1",
        ],
        run_.root,
    )
    m = re.search(r"(\d+) commits scanned", out)
    commits = m.group(1) if m else "?"
    if code != 0:
        return failed("secrets", f"gitleaks over {commits} commits: {last_line(out)}")
    code, tree, err = run_parts(
        ["uv", "run", "python", "scripts/submit_check.py", "--secrets-only"], run_.root
    )
    if code != 0:
        return failed("secrets", f"the tree scan: {said(tree, err)}")
    return passed(
        "secrets",
        f"gitleaks: {commits} commits on every branch, tag and pull request head and HEAD, "
        f"no leaks; {said(tree, err)}",
    )


def step_notes(run_: Run) -> Step:
    root = run_.root
    _, files = run(["git", "ls-files", "--", INTERNAL], root)
    if not files.strip():
        left = mentions(root)
        if left:
            return failed("notes", f"{INTERNAL} is gone but these still name it: {left}")
        return skipped("notes", f"the tip has no {INTERNAL}; nothing to remove")
    removed = len(files.splitlines())
    rows = mentions(root)
    code, out = run(["git", "rm", "-r", "-q", INTERNAL], root)
    if code == 0:
        for path, _ in rows:
            file = root / path
            file.write_text(rewrite(file.read_text(encoding="utf-8")), encoding="utf-8")
        left = mentions(root)
        if left:
            code, out = 1, f"mentions left after the rewrite: {left}"
    for cmd in (["git", "add", "-u"], ["git", "commit", "-q", "-m", COMMIT_MESSAGE]):
        if code != 0:
            break
        code, out = run(cmd, root)
    if code != 0:
        # The tree was clean when the run began (start refuses otherwise, and the dry run works
        # in a fresh worktree), so this puts back only what this step changed.
        run(["git", "reset", "-q", "--hard", "HEAD"], root)
        return failed("notes", f"stopped and put the tree back: {last_line(out)}")
    _, sha = run(["git", "rev-parse", "--short", "HEAD"], root)
    return passed(
        "notes",
        f"removed {removed} files under {INTERNAL} and reworded "
        f"{sum(c for _, c in rows)} mentions in {len(rows)} files, in commit {sha}; "
        f"{len(READERS)} readers keep the path and cope without it",
    )


def step_tests(run_: Run) -> Step:
    code, out, err = run_parts(["make", "lint"], run_.root)
    if code != 0:
        return failed("tests", f"make lint: {said(out, err)}")
    # The project's own pytest options (-q, no cache folder) print the "N passed" line last.
    code, out, err = run_parts(["uv", "run", "pytest"], run_.root)
    first = next((ln for ln in out.splitlines() if ln.startswith(("FAILED", "ERROR"))), "")
    if code != 0:
        return failed("tests", f"pytest: {first or said(out, err)}")
    return passed("tests", f"make lint clean; pytest: {said(out, err)}")


def step_submit(run_: Run) -> Step:
    code, out, err = run_parts(["make", "submit-check"], run_.root)
    blocker = submit_blocker(code, out)
    found = SUBMIT_SUMMARY.findall(out)
    summary = f"submit-check: {found[-1][0]} failed: {found[-1][1]}" if found else last_line(err)
    if blocker:
        return failed("submit", f"{summary}; {blocker}")
    return passed("submit", f"{summary}; the flip makes the repo public")


def step_readme(run_: Run) -> Step:
    html, who = render_readme(run_)
    dead, blocked, n_images, n_links = readme_problems(run_, html)
    if not ci_badge(run_.images, run_.slug):
        dead.append("the README shows no CI badge for this repository")
    seen = f"rendered by {who}: {n_images} images and {n_links} links"
    if dead:
        return failed("readme", f"{seen}; {len(dead)} dead: " + "; ".join(dead[:4]))
    note = f"; blocked to scripts, so open by hand: {', '.join(blocked)}" if blocked else ""
    return passed("readme", f"{seen}, every one answers{note}")


def step_changelog(run_: Run) -> Step:
    path = run_.root / CHANGELOG
    if not path.is_file():
        return failed("changelog", f"{CHANGELOG} is missing")
    notes = release_notes(path.read_text(encoding="utf-8"))
    if not notes:
        return failed("changelog", f"{CHANGELOG} has no ## {TAG} section with text in it")
    run_.notes = notes
    days = commit_days(run_.root)
    if days is None:
        return failed("changelog", "git log failed")
    wanted = {d for d in days if FIRST_DAY <= d < run_.today}
    missing = sorted(wanted - days_named(notes))
    if missing:
        names = ", ".join(d.strftime("%a %b %-d") for d in missing)
        return failed("changelog", f"{CHANGELOG} has no ### line for {names}, which have commits")
    return passed(
        "changelog",
        f"{CHANGELOG} {TAG} names every day with commits from {FIRST_DAY:%b %-d} to yesterday "
        f"({len(wanted)} days)",
    )


# ---------------------------------------------------------------------------------------------
# The flip and after


def visibility(run_: Run) -> str | None:
    code, out, _err = run_parts(
        ["gh", "repo", "view", run_.slug, "--json", "visibility"], run_.root
    )
    try:
        return str(json.loads(out)["visibility"]).upper() if code == 0 else None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def step_push(run_: Run) -> Step:
    code, out = run(["git", "push", "-q", "origin", "main"], run_.root)
    if code != 0:
        return failed("push", f"git push origin main: {last_line(out)}")
    _, sha = run(["git", "rev-parse", "--short", "HEAD"], run_.root)
    return passed("push", f"origin main is at {sha}")


def step_flip(run_: Run) -> Step:
    before = visibility(run_)
    if before == "PUBLIC":
        return skipped("flip", f"{run_.slug} is already public")
    if before is None:
        return failed("flip", f"gh cannot read {run_.slug}'s visibility")
    code, out = run(public_cmd(run_.slug), run_.root)
    if code != 0:
        return failed("flip", f"gh repo edit: {last_line(out)}")
    after = visibility(run_)
    if after != "PUBLIC":
        return failed("flip", f"gh repo edit answered, and GitHub still says {after}")
    return passed("flip", f"{run_.slug} was {before}, is PUBLIC")


def logged_out_env() -> dict[str, str]:
    """No GitHub token, no curl config and a home with nothing in it: a stranger's view."""
    home = tempfile.mkdtemp(prefix="go-public-stranger-")
    # The system folders and curl's own, not this shell's PATH: nothing of this session goes along.
    curl_dir = str(Path(shutil.which("curl") or "/usr/bin/curl").parent)
    return {"PATH": f"{curl_dir}:/usr/bin:/bin", "HOME": home, "LC_ALL": "C"}


def curl(url: str, env: Mapping[str, str], cwd: Path, body: bool = False) -> tuple[int, str, str]:
    """The status, the content type and (when asked) the body, as a logged out visitor gets them.
    -q first, so no .curlrc is read; no -b, so no cookie is sent."""
    cmd = ["curl", "-q", "-sS", "-L", "--max-time", "30", "-o", "-" if body else os.devnull]
    code, out, err = run_parts([*cmd, "-w", "\n%{http_code} %{content_type}", url], cwd, env)
    text, _, tail = out.rpartition("\n")
    status, _, ctype = tail.partition(" ")
    if code != 0 or not status.isdigit():
        return 0, "", last_line(err)
    return int(status), ctype, text


def step_public(run_: Run) -> Step:
    badge = ci_badge(run_.images, run_.slug)
    live = live_link(run_.root)
    page = f"https://github.com/{run_.slug}"
    wanted: dict[str, str] = {page: "the README page"}
    for src in run_.images:
        url = src if re.match(r"https?://", src) else f"{page}/raw/main/{src.lstrip('/')}"
        wanted[url] = "the CI badge" if src == badge else "an image"
    if live:
        wanted[live] = "the live link"
    env = logged_out_env()
    problems: dict[str, str] = {}
    todo = list(wanted)
    for attempt in range(run_.attempts):
        problems = {}
        for url in todo:
            status, ctype, text = curl(url, env, run_.root, body=url == page)
            if status != 200:
                problems[url] = f"{wanted[url]} {url} answered {status or text or 'nothing'}"
            elif url == page and "Second Look" not in text:
                problems[url] = f"the README page {url} does not show the README"
            elif wanted[url] == "the CI badge" and "svg" not in ctype:
                problems[url] = f"the CI badge {url} came back as {ctype or 'nothing'}"
        todo = list(problems)
        if not todo or attempt == run_.attempts - 1:
            break
        run_.sleep(run_.wait)  # GitHub can take a moment to serve a repository it just opened
    shutil.rmtree(env["HOME"], ignore_errors=True)
    if not badge:
        problems["badge"] = "the README shows no CI badge"
    if not live:
        problems["live"] = "docs/devpost.md's Live link field holds no link"
    if problems:
        return failed("public", "logged out: " + "; ".join(list(problems.values())[:4]))
    images = sum(1 for kind in wanted.values() if kind in ("an image", "the CI badge"))
    return passed(
        "public",
        f"logged out, no token or cookie: the README page, {images} images with the CI badge, "
        f"and the live link {live} all answer 200",
    )


def notes_file(run_: Run, folder: Path) -> Path:
    path = folder / "notes.md"
    path.write_text(run_.notes + "\n", encoding="utf-8")
    return path


def step_tag(run_: Run) -> Step:
    root = run_.root
    _, head = run(["git", "rev-parse", "HEAD"], root)
    code, sha = run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{TAG}^{{commit}}"], root)
    there = code == 0
    if there and sha != head:
        return failed("tag", f"{TAG} already names {sha[:7]}, not the tip {head[:7]}; not moved")
    if not there:
        with tempfile.TemporaryDirectory() as tmp:
            message = Path(tmp) / "tag.md"
            message.write_text(f"{RELEASE_TITLE}\n\n{run_.notes}\n", encoding="utf-8")
            code, out = run(["git", "tag", "-a", TAG, "-F", str(message)], root)
        if code != 0:
            return failed("tag", f"git tag: {last_line(out)}")
    code, out = run(["git", "push", "-q", "origin", f"refs/tags/{TAG}"], root)
    if code != 0:
        return failed("tag", f"git push of {TAG}: {last_line(out)}")
    if there:
        return skipped("tag", f"{TAG} was already on {head[:7]}; pushed")
    return passed("tag", f"{TAG} made on {head[:7]} with the notes from {CHANGELOG}, and pushed")


def step_release(run_: Run) -> Step:
    code, out = run(
        ["gh", "release", "view", TAG, "--repo", run_.slug, "--json", "url", "--jq", ".url"],
        run_.root,
    )
    if code == 0:
        return skipped("release", f"already there: {last_line(out)}")
    with tempfile.TemporaryDirectory() as tmp:
        notes = notes_file(run_, Path(tmp))
        code, out = run(
            [
                "gh",
                "release",
                "create",
                TAG,
                "--repo",
                run_.slug,
                "--title",
                RELEASE_TITLE,
                "--notes-file",
                str(notes),
                "--verify-tag",
            ],
            run_.root,
        )
    if code != 0:
        return failed("release", f"gh release create: {last_line(out)}")
    return passed("release", f"{RELEASE_TITLE}: {last_line(out)}")


BEFORE_FLIP: list[Callable[[Run], Step]] = [
    step_secrets,
    step_notes,
    step_tests,
    step_submit,
    step_readme,
    step_changelog,
]
FROM_FLIP: list[Callable[[Run], Step]] = [step_push, step_flip, step_public, step_tag, step_release]
STEP_NAMES = ["start", *(f.__name__.removeprefix("step_") for f in [*BEFORE_FLIP, *FROM_FLIP])]


# ---------------------------------------------------------------------------------------------
# The throwaway worktree for GO=dry


def make_worktree(checkout: Path) -> tuple[Path | None, str]:
    folder = Path(tempfile.mkdtemp(prefix="go-public-dry-"))
    tree = folder / "tree"
    code, out = run(["git", "worktree", "add", "--detach", "--quiet", str(tree), "HEAD"], checkout)
    if code != 0:
        shutil.rmtree(folder, ignore_errors=True)
        return None, last_line(out)
    return tree, ""


def remove_worktree(checkout: Path, tree: Path) -> None:
    run(["git", "worktree", "remove", "--force", str(tree)], checkout)
    run(["git", "worktree", "prune"], checkout)
    shutil.rmtree(tree.parent, ignore_errors=True)


# ---------------------------------------------------------------------------------------------


def plan(checkout: Path, slug: str = REPO_SLUG) -> int:
    rows = mentions(checkout)
    print("go-public: nothing changes. make go-public GO=dry runs every step before the flip in")
    print("a throwaway worktree and stops; make go-public GO=yes runs them all, on main.")
    steps = next(p for p in (__doc__ or "").split("\n\n") if p.startswith("  start"))
    print(steps)
    print("The flip runs: " + " ".join(public_cmd(slug)))
    print(f"The notes step would git rm -r {INTERNAL} and reword {sum(c for _, c in rows)}")
    print(f"mentions in {len(rows)} files:")
    for path, count in rows:
        print(f"    {path}: {count}")
    print("These keep the path, because code opens it, and each copes once the folder is gone:")
    for path, how in READERS.items():
        print(f"    {path}: {how}")
    print(f"(from the tip only: the git history still holds {INTERNAL})")
    return 0


def write_json(path: Path, steps: list[Step], dry: bool, note: str, commit: str) -> None:
    ran = [s.name for s in steps]
    report = {
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "GO=dry (--no-flip)" if dry else "GO=yes",
        "note": note,
        "commit": commit,
        "failed": [s.name for s in steps if s.failed],
        "steps": [{"step": s.name, "result": s.result, "output": s.output} for s in steps],
        "not_run": [n for n in STEP_NAMES if n not in ran],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--yes", action="store_true", help="do it all, the flip included")
    parser.add_argument(
        "--no-flip",
        action="store_true",
        help="run every step before the flip in a throwaway worktree, then stop (GO=dry)",
    )
    parser.add_argument("--repo", default=REPO_SLUG, help="the GitHub repository, owner/name")
    parser.add_argument("--json", type=Path, default=None, help="also write the steps here")
    parser.add_argument("--note", default="", help="a sentence the JSON carries about this run")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    checkout = args.root.resolve()
    if not (args.yes or args.no_flip):
        return plan(checkout, args.repo)
    dry = args.no_flip
    _, commit = run(["git", "rev-parse", "--short", "HEAD"], checkout)
    steps: list[Step] = []

    def record(step: Step) -> bool:
        print(step.line(), flush=True)
        steps.append(step)
        return not step.failed

    run_ = Run(root=checkout, slug=args.repo, dry=dry)
    tree: Path | None = None
    try:
        going = record(step_start(checkout, dry))
        if dry:
            tree, why = make_worktree(checkout)
            if tree is None:
                going = record(failed("worktree", f"git worktree add failed: {why}"))
            else:
                run_.root = tree
        # A dry run works only in its throwaway worktree, never in the checkout it was run from.
        if (going and not dry) or tree is not None:
            for fn in BEFORE_FLIP:
                if not record(fn(run_)) and not dry:
                    break
        if not dry and not any(s.failed for s in steps):
            for fn in FROM_FLIP:
                if not record(fn(run_)):
                    break
    finally:
        if tree is not None:
            remove_worktree(checkout, tree)
    if args.json:
        write_json(args.json, steps, dry, args.note, commit)
    bad = [s.name for s in steps if s.failed]
    tail = "; stopped before the push and the flip, as GO=dry does" if dry else ""
    print(f"go-public: {len(steps)} steps, {len(bad)} failed: {', '.join(bad) or 'none'}{tail}")
    if not dry and not bad:
        print(f"go-public: {args.repo} is public, tagged {TAG} and released")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
