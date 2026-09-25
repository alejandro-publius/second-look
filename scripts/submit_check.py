"""The submission gate: every item in docs/SUBMISSION_CHECKLIST.md that a script can check.

Run: make submit-check  (uv run python scripts/submit_check.py [--video path.mp4])
     make secrets runs only the working tree secret scan (--secrets-only), inside make check.
Prints one line per check and ends with "submit-check: N failed: <names>". Exit 1 on any failure.
Until submission day the expected failures are the video link and the public repo, and no other.
The Devpost text (docs/devpost.md) is held to the form: the track statement as its first line,
every field filled, every number in a field backed by results/, the report named as an
attachment, and both team members named (UPDATE_30 section 8 item 2).
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
from scripts.verify_claims import CLAIM_RE

ROOT = Path(__file__).resolve().parents[1]
# The repository by name, so gh asks GitHub about it from any clone, even one whose remote is a
# folder on this Mac (the go-public dry run's local mirror).
REPO_SLUG = "alejandro-publius/second-look"
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

# The Devpost form, field by field, as docs/devpost.md heads them. Each is one ```text block.
DEVPOST = Path("docs/devpost.md")
TRACK_FIELD = "Track statement (line one of the description)"
VIDEO_FIELD = "Video link"
LIVE_FIELD = "Live link"
DEVPOST_FIELDS = (
    "Project name",
    "Tagline (under 200 characters)",
    TRACK_FIELD,
    *HEADERS,
    "Users and impact on ecosystem and human health",
    "Built with",
    LIVE_FIELD,
    "Judges link",
    "Repository",
    VIDEO_FIELD,
)
TEAM = ("Alex Velazquez", "Rachel Selbrede")
REPORT_PDF = Path("docs/REPORT.pdf")
SECTION_RE = re.compile(r"^## (.+?)\s*$", re.M)
TEXT_BLOCK_RE = re.compile(r"^```text\n(.*?)^```", re.M | re.S)
STATED_COUNT_RE = re.compile(r"^(\d+) characters\s*$", re.M)
# The video link's slot. Only the video_link check reads it, so a slot left open fails that
# check and no other: the day's expected failure stays one line.
VIDEO_SLOT_RE = re.compile(r"\[VIDEO LINK[^\]]*\]")
# A word left to fill, or a slot in capitals such as [VIDEO LINK]; a Markdown link such as
# [model card](...) is not one.
PLACEHOLDER_RE = re.compile(
    r"(?i:\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b|lorem ipsum)|\[[A-Z][A-Z0-9 _-]{2,}(?::[^\]]*)?\]"
)
# A number as a reader meets it, not a digit inside a name such as hl7, cloudflare-d1 or b907cf0.
NUMBER_RE = re.compile(r"(?<![\w./#@-])\d+(?:,\d{3})*(?:\.\d+)?(?![\w/])")
# Numbers in the Devpost text that are names or fixed facts, not results, each with its reason.
# Every other number in a field needs a claim marker in its section, which verify_claims checks
# against results/.
DEVPOST_FIXED = {
    "Track 3": "the track's own name",
    "(2026), page 9": "where the policy brief is cited",
    '"4 of 4 on built banks, tested Sep 23"': "an example of what an analyst reads, not a result",
    "FHIR R4 4.0.1": "the FHIR version",
    "SUSHI 3.20.1": "the tool version that built the guide",
    "72 hours": "the rain window the dry pipe rule reads, set in code (below)",
    "30 days": "how long an upload is kept, set in code (below)",
    "Opus 5.5": "a model's name",
    "Fable 5.1": "a model's name",
    "Haiku 4.5": "a model's name",
    "Sonnet 5": "a model's name",
    "CC BY-SA 4.0": "a licence's name",
}
DEVPOST_LIMITS = {"Tagline (under 200 characters)": 200}
# The fixed facts that code sets: the code must still say the same, or the text has gone stale.
DEVPOST_FIXED_IN_CODE = {
    "72 hours": ("core/rainfall.py", re.compile(r"^DEFAULT_WINDOW_HOURS = 72$", re.M)),
    "30 days": ("worker/src/uploads.ts", re.compile(r"^export const KEEP_DAYS = 30;$", re.M)),
}
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
    """NEXT_PUBLIC_SITE_URL, else the Devpost text's Live link field, else a line naming a demo."""
    if env_url:
        return env_url
    text = _text(root / "docs" / "devpost.md")
    live = (field_text(devpost_sections(text).get(LIVE_FIELD, "")) or "").strip()
    if URL_RE.fullmatch(live):
        return live
    for line in text.splitlines():
        if "demo" in line.lower():
            m = URL_RE.search(line)
            if m:
                return m.group(0)
    return None


def devpost_sections(text: str) -> dict[str, str]:
    """Each "## " heading of the Devpost text and everything under it, up to the next one."""
    marks = list(SECTION_RE.finditer(text))
    return {
        m.group(1): text[m.end() : marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        for i, m in enumerate(marks)
    }


def field_text(section: str) -> str | None:
    """What gets pasted for a field: its ```text block, or None when the section has none."""
    m = TEXT_BLOCK_RE.search(section)
    return m.group(1).rstrip("\n") if m else None


def devpost_track_problems(text: str, statement: str) -> list[str]:
    problems = []
    first = text.splitlines()[0].strip() if text.strip() else ""
    if first != statement:
        problems.append(f"{DEVPOST}'s first line is not the track statement word for word")
    block = field_text(devpost_sections(text).get(TRACK_FIELD, ""))
    if block is None:
        problems.append(f"{DEVPOST} has no '{TRACK_FIELD}' field")
    elif block.strip() != statement:
        problems.append(f"the '{TRACK_FIELD}' field is not the track statement word for word")
    return problems


def devpost_field_problems(text: str) -> tuple[list[str], list[str]]:
    """Every field there, filled, with no placeholder, and under its limit: the problems, then
    notes. A stated count that is off is a note, not a failure: pasting the video link into the
    demonstration field changes its length on the very day the link arrives."""
    sections = devpost_sections(text)
    problems: list[str] = []
    notes: list[str] = []
    for name in DEVPOST_FIELDS:
        if name == VIDEO_FIELD:
            continue  # the video_link check owns the video's slot
        block = field_text(sections[name]) if name in sections else None
        if name not in sections:
            problems.append(f"{DEVPOST} has no '{name}' field")
            continue
        if block is None or not block.strip():
            problems.append(f"the '{name}' field is empty")
            continue
        slot = PLACEHOLDER_RE.search(VIDEO_SLOT_RE.sub(" ", block))
        if slot:
            problems.append(f"the '{name}' field holds a placeholder: {slot.group(0)}")
        stated = STATED_COUNT_RE.search(sections[name])
        if stated and int(stated.group(1)) != len(block):
            notes.append(f"'{name}' says {stated.group(1)} characters and has {len(block)}")
        limit = DEVPOST_LIMITS.get(name)
        if limit is not None and len(block) >= limit:
            problems.append(f"the '{name}' field has {len(block)} characters, not under {limit}")
    return problems, notes


def _number(token: str) -> str:
    return token.replace(",", "")


def devpost_number_problems(root: Path, text: str) -> list[str]:
    """Every number in a field has a claim marker in its section, or is a named fixed fact."""
    problems = []
    for name, section in devpost_sections(text).items():
        block = field_text(section)
        if block is None:
            continue
        claimed = {_number(m.group(3)) for m in CLAIM_RE.finditer(section) if m.group(3)}
        plain = URL_RE.sub(" ", VIDEO_SLOT_RE.sub(" ", block))
        for phrase in sorted(DEVPOST_FIXED, key=len, reverse=True):
            plain = plain.replace(phrase, " ")
        for m in NUMBER_RE.finditer(plain):
            if _number(m.group(0)) not in claimed:
                problems.append(
                    f"the '{name}' field says {m.group(0)} with no claim marker for it in its "
                    "section, and it is not a fixed fact"
                )
    for phrase, (rel, pattern) in DEVPOST_FIXED_IN_CODE.items():
        if phrase in text and not pattern.search(_text(root / rel)):
            problems.append(f"the Devpost text says {phrase}, and {rel} no longer sets it")
    return problems


def devpost_report_problems(root: Path, text: str) -> list[str]:
    problems = []
    if not re.search(r"(?i)\battach\b[^\n]*" + re.escape(str(REPORT_PDF)), text):
        problems.append(f"{DEVPOST} does not name {REPORT_PDF} as an attachment")
    pdf = root / REPORT_PDF
    if not pdf.is_file():
        problems.append(f"{REPORT_PDF} is missing")
    elif pdf.read_bytes()[:5] != b"%PDF-":
        problems.append(f"{REPORT_PDF} is not a PDF")
    return problems


def devpost_team_problems(text: str) -> list[str]:
    sections = devpost_sections(text)
    if "Team" not in sections:
        return [f"{DEVPOST} has no Team section"]
    return [f"the Team section does not name {n}" for n in TEAM if n not in sections["Team"]]


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

    # The organizers' five headers: in order in the Devpost text, which is what they read, and each
    # named word for word in the README's line that maps them to its judge-first sections
    # (UPDATE_27 section 3 set the README's order; the headers moved to that line).
    headers = Check("five_headers")
    devpost_text = (
        (root / "docs" / "devpost.md").read_text(encoding="utf-8")
        if (root / "docs" / "devpost.md").exists()
        else ""
    )
    positions = [devpost_text.find(h) for h in HEADERS]
    for h, pos in zip(HEADERS, positions, strict=True):
        if pos < 0:
            headers.reasons.append(f"docs/devpost.md lacks the organizer header '{h}'")
    if all(p >= 0 for p in positions) and positions != sorted(positions):
        headers.reasons.append("the five organizer headers are out of order in docs/devpost.md")
    map_line = next(
        (
            ln
            for ln in readme_lines
            if ln.startswith("How this answers the organizers' five headers")
        ),
        "",
    )
    for h in HEADERS:
        if f"*{h}*" not in map_line:
            headers.reasons.append(f"README.md's map line does not name '{h}'")
    checks.append(headers)

    # UPDATE_30 section 8 item 2: the Devpost text as the form will hold it.
    first = Check("devpost_track_statement")
    first.reasons.extend(devpost_track_problems(devpost_text, statement) if statement else [])
    if not statement:
        first.reasons.append("docs/track_statement.md missing or empty")
    checks.append(first)

    fields = Check("devpost_fields")
    problems, notes = devpost_field_problems(devpost_text)
    fields.reasons.extend(problems)
    fields.notes.extend(notes)
    checks.append(fields)

    numbers = Check("devpost_numbers")
    numbers.reasons.extend(devpost_number_problems(root, devpost_text))
    rc, out = run(["uv", "run", "python", "scripts/verify_claims.py", "--file", str(DEVPOST)])
    if rc != 0:
        numbers.reasons.append(f"verify_claims --file {DEVPOST} failed: {_last_line(out)}")
    checks.append(numbers)

    attached = Check("devpost_report")
    attached.reasons.extend(devpost_report_problems(root, devpost_text))
    checks.append(attached)

    team = Check("devpost_team")
    team.reasons.extend(devpost_team_problems(devpost_text))
    checks.append(team)

    link = Check("video_link")
    devpost = root / "docs" / "devpost.md"
    if not video_links(readme):
        link.reasons.append("README.md has no line with the word video and a link")
    if not devpost.exists():
        link.reasons.append("docs/devpost.md missing")
    else:
        if not video_links(devpost_text):
            link.reasons.append("docs/devpost.md has no line with the word video and a link")
        slot = VIDEO_SLOT_RE.search(devpost_text)
        if slot:
            link.reasons.append(f"docs/devpost.md still holds the video's slot {slot.group(0)}")
        video_field = field_text(devpost_sections(devpost_text).get(VIDEO_FIELD, "")) or ""
        if not URL_RE.fullmatch(video_field.strip()):
            link.reasons.append(f"the '{VIDEO_FIELD}' field in docs/devpost.md holds no link")
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
    rc, out = run(["gh", "repo", "view", REPO_SLUG, "--json", "visibility"])
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
