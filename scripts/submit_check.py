"""The submission gate: every item in docs/SUBMISSION_CHECKLIST.md that a script can check.

Run: make submit-check  (uv run python scripts/submit_check.py [--video path.mp4])
     make secrets runs only the working tree secret scan (--secrets-only), inside make check.
Prints one line per check and ends with "submit-check: N failed: <names>". Exit 1 on any failure.
Until submission day the expected failures are: the video link, the public repo, and real
(not synthetic) results.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from scripts import audit_log

ROOT = Path(__file__).resolve().parents[1]
Runner = Callable[[list[str]], tuple[int, str]]
Fetch = Callable[[str], int]
HEADERS = [
    "The problem",
    "How the solution aligns with OneAquaHealth",
    "Innovation and practical value",
    "Effective use of data, technology, AI, APIs and standards",
    "A clear demonstration of what was built",
]
URL_RE = re.compile(r"https?://[^\s)>\]]+")
# A name that ends in a secret word, as EXPORT_TOKEN, QA_KEY and NEXT_PUBLIC_QA_KEY do in .env and
# worker/.dev.vars, and export_token does in code. The made up values never count: change-me is
# the placeholder .env.example and apps/api/settings.py ship with, test- starts the ones in the
# test suites, and e2e- the key worker/test/e2e.mjs gives its own local Worker.
SECRET_NAME = r"(api[_-]?key|secret([_-]?key)?|token|password|qa[_-]?key)"
NOT_PLACEHOLDER = r"(?!change-me|test-|e2e-)"
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Anthropic key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "OpenAI style key": re.compile(r"\bsk-[A-Za-z0-9]{32,}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "Slack token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "assigned secret": re.compile(
        rf"(?i){SECRET_NAME}\s*[:=]\s*['\"]{NOT_PLACEHOLDER}[A-Za-z0-9/+_=-]{{20,}}['\"]"
    ),
    # The same without quotes, as a .env line has it. The value has to end the line, so code
    # such as token = new_contributor_token() is not a hit.
    "secret in a .env line": re.compile(
        rf"(?im){SECRET_NAME}\s*=\s*{NOT_PLACEHOLDER}[A-Za-z0-9/+_=-]{{20,}}\s*$"
    ),
}
# Files that hold local secrets: .env and its kind for the API, .dev.vars for wrangler dev.
# .gitignore keeps them out in every folder; one that git would still pick up fails the scan.
LOCAL_SECRET_FILE = re.compile(r"\.(env|dev\.vars)(\..+)?")
LOCAL_SECRET_EXAMPLE = ".env.example"
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".jar",
    ".zip",
    ".woff",
    ".woff2",
}
SKIP_DIRS = {".git", "node_modules", ".venv", ".next", "__pycache__", ".mypy_cache", ".ruff_cache"}


@dataclass
class Check:
    name: str
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.reasons


def default_runner(root: Path) -> Runner:
    def run(argv: list[str]) -> tuple[int, str]:
        try:
            proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as e:
            return 1, f"could not run {' '.join(argv)}: {e}"
        return proc.returncode, proc.stdout + proc.stderr

    return run


def default_fetch(url: str) -> int:
    try:
        return httpx.get(url, timeout=15, follow_redirects=True).status_code
    except httpx.HTTPError:
        return 0


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _last_line(text: str) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "(no output)"


def candidate_files(root: Path, run: Runner) -> list[Path]:
    """Tracked plus untracked-but-not-ignored files; falls back to a walk outside a git repo."""
    rc, out = run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"])
    if rc == 0 and out:
        return [root / p for p in out.split("\0") if p]
    return [
        p
        for p in root.rglob("*")
        if p.is_file() and not (SKIP_DIRS & set(p.relative_to(root).parts))
    ]


def scan_secrets(root: Path, files: list[Path]) -> list[str]:
    hits: list[str] = []
    for path in files:
        if LOCAL_SECRET_FILE.fullmatch(path.name) and path.name != LOCAL_SECRET_EXAMPLE:
            hits.append(f"{path.relative_to(root)}: a local secrets file that is not ignored")
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(line):
                    hits.append(f"{path.relative_to(root)}:{n}: looks like a {label}")
    return hits


def video_links(text: str) -> list[str]:
    return [
        m.group(0)
        for line in text.splitlines()
        if "video" in line.lower()
        for m in URL_RE.finditer(line)
    ]


def demo_url(root: Path, env_url: str | None) -> str | None:
    if env_url:
        return env_url
    for line in _text(root / "docs" / "devpost.md").splitlines():
        if "demo" in line.lower():
            m = URL_RE.search(line)
            if m:
                return m.group(0)
    return None


def run_checks(
    root: Path,
    *,
    runner: Runner | None = None,
    fetch: Fetch | None = None,
    video: Path | None = None,
    env_url: str | None = None,
) -> list[Check]:
    root = root.resolve()
    run = runner or default_runner(root)
    get = fetch or default_fetch
    checks: list[Check] = []
    readme = _text(root / "README.md")
    readme_lines = [ln.strip() for ln in readme.splitlines() if ln.strip()]

    track = Check("track_statement")
    statement = _text(root / "docs" / "track_statement.md").strip()
    if not statement:
        track.reasons.append("docs/track_statement.md missing or empty")
    elif not readme_lines or readme_lines[0] != statement:
        track.reasons.append("README.md's first line is not the track statement word for word")
    checks.append(track)

    headers = Check("five_headers")
    positions = [readme.find(f"## {h}") for h in HEADERS]
    for h, pos in zip(HEADERS, positions, strict=True):
        if pos < 0:
            headers.reasons.append(f"README.md lacks the header '## {h}'")
    if all(p >= 0 for p in positions) and positions != sorted(positions):
        headers.reasons.append("the five organizer headers are out of order in README.md")
    checks.append(headers)

    link = Check("video_link")
    devpost = root / "docs" / "devpost.md"
    if not video_links(readme):
        link.reasons.append("README.md has no line with the word video and a link")
    if not devpost.exists():
        link.reasons.append("docs/devpost.md missing")
    elif not video_links(_text(devpost)):
        link.reasons.append("docs/devpost.md has no line with the word video and a link")
    checks.append(link)

    duration = Check("video_duration")
    if video is None:
        duration.notes.append("no --video file given, so the 3 to 5 minute check was skipped")
    elif not shutil.which("ffprobe"):
        duration.notes.append("ffprobe is not installed, so the duration check was skipped")
    elif not video.is_file():
        duration.reasons.append(f"video file not found: {video}")
    else:
        rc, out = run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(video),
            ]
        )
        try:
            seconds = float(_last_line(out))
        except ValueError:
            seconds = -1.0
        if rc != 0 or seconds < 0:
            duration.reasons.append(f"ffprobe could not read {video.name}: {_last_line(out)}")
        elif not 180 <= seconds <= 300:
            duration.reasons.append(f"video runs {seconds:.0f} s; it must be 180 to 300 s")
        else:
            duration.notes.append(f"video runs {seconds:.0f} s")
    checks.append(duration)

    lic = Check("license")
    text = _text(root / "LICENSE")
    if not text:
        lic.reasons.append("LICENSE file missing")
    elif "MIT" not in text:
        lic.reasons.append("LICENSE does not say MIT")
    checks.append(lic)

    demo = Check("demo_url")
    url = demo_url(root, env_url)
    if url is None:
        demo.notes.append("NEXT_PUBLIC_SITE_URL unset and no demo link in docs/devpost.md; skipped")
    else:
        status = get(url)
        if status != 200:
            demo.reasons.append(f"{url} answered {status or 'nothing'}, not 200")
        else:
            demo.notes.append(f"{url} answered 200")
    checks.append(demo)

    secrets = Check("secrets_scan")
    secrets.reasons.extend(scan_secrets(root, candidate_files(root, run)))
    if shutil.which("gitleaks") and (root / ".git").exists():
        rc, out = run(
            ["gitleaks", "git", str(root), "--no-banner", "--redact", "-v", "--exit-code", "1"]
        )
        if rc != 0:
            where = re.findall(r"^File:\s+(\S+)\n(?:.*\n)*?Line:\s+(\d+)", out, re.MULTILINE)
            spots = ", ".join(f"{f}:{ln}" for f, ln in where) or _last_line(out)
            secrets.reasons.append(
                f"gitleaks flagged the history at {spots}; if these are fake test values, "
                "add their fingerprints to .gitleaksignore"
            )
        else:
            secrets.notes.append("gitleaks: history clean")
    else:
        secrets.notes.append("gitleaks not run (not installed or not a git checkout)")
    checks.append(secrets)

    claims = Check("verify_claims")
    rc, out = run(["uv", "run", "python", "scripts/verify_claims.py"])
    if rc != 0:
        claims.reasons.append(f"verify_claims without --synthetic failed: {_last_line(out)}")
    checks.append(claims)

    audit = Check("audit_log")
    try:
        n = audit_log.verify(root / "audit" / "log.jsonl")
    except audit_log.AuditError as e:
        audit.reasons.append(f"audit log broken: {e}")
    else:
        audit.notes.append(
            f"{n} entries, last hash {audit_log.last_hash(root / 'audit' / 'log.jsonl')}"
        )
    checks.append(audit)

    public = Check("repo_public")
    rc, out = run(["gh", "repo", "view", "--json", "visibility"])
    visibility = None
    if rc == 0:
        try:
            visibility = json.loads(out).get("visibility")
        except (json.JSONDecodeError, AttributeError):
            visibility = None
    if visibility is None:
        public.reasons.append(f"cannot tell if the repo is public (gh said: {_last_line(out)})")
    elif str(visibility).upper() != "PUBLIC":
        public.reasons.append(f"GitHub repo is {visibility}; it goes public on Sep 30")
    checks.append(public)
    return checks


def report(checks: list[Check]) -> int:
    failed = [c for c in checks if not c.passed]
    for c in checks:
        mark = "PASS" if c.passed else "FAIL"
        note = f"  ({'; '.join(c.notes)})" if c.notes else ""
        print(f"{mark}  {c.name}{note}")
        for reason in c.reasons:
            print(f"      {reason}")
    names = ", ".join(c.name for c in failed) if failed else "none"
    print(f"submit-check: {len(failed)} failed: {names}")
    return len(failed)


def tree_secrets(root: Path) -> int:
    """The working tree half of secrets_scan, for make secrets inside make check.

    make secrets runs gitleaks over the history first, so this reads only the files git would
    commit: tracked ones and untracked ones that are not ignored. It names the file and line of a
    hit, never the value.
    """
    files = candidate_files(root, default_runner(root))
    hits = scan_secrets(root, files)
    for hit in hits:
        print(f"FAIL  {hit}")
    print(f"secrets: {len(hits)} found in the {len(files)} files git would commit")
    return 1 if hits else 0


def main(argv: list[str] | None = None) -> int:
    import os

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--video", type=Path, default=None, help="local video file to time")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument(
        "--secrets-only",
        action="store_true",
        help="only scan the working tree for secrets, as make secrets does",
    )
    args = parser.parse_args(argv)
    if args.secrets_only:
        return tree_secrets(args.root.resolve())
    checks = run_checks(args.root, video=args.video, env_url=os.environ.get("NEXT_PUBLIC_SITE_URL"))
    return 1 if report(checks) else 0


if __name__ == "__main__":
    sys.exit(main())
