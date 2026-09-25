"""Which Worker version and which Pages build are live, and which were last known good.

scripts/deploy.sh calls this after every production deploy. It writes one row into the marked
block of docs/notes/hosting.md: the part (worker or web), the commit, the Worker's version id or
the Pages deployment's id, and for the site the folder where the exact files that went up are kept
(`~/second-look-backups/deploys/`), since Pages cannot roll back from the command line and the
only way back is to upload the same files again. A row is "no" until the phone tests pass against
production; then `good` marks it "yes". `make rollback` (scripts/rollback.py) goes back to the
newest good row that is not what is live now.

  uv run python scripts/deploy_record.py record worker --output-file <wrangler deploy output>
  uv run python scripts/deploy_record.py record web --output-file <pages deploy output>
  uv run python scripts/deploy_record.py good          mark the newest commit's rows good
  uv run python scripts/deploy_record.py show
  uv run python scripts/deploy_record.py check-live    exit 0 when what is live is a good row
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from scripts.outward import Outward

ROOT = Path(__file__).resolve().parents[1]
HOSTING = ROOT / "docs" / "notes" / "hosting.md"
START = "<!-- deploys:start -->"
END = "<!-- deploys:end -->"
HEAD = "| When (UTC) | Part | Commit | Id | Archive | Checked |"
RULE = "|---|---|---|---|---|---|"
KEEP_ROWS = 20
# Uploads of the site are large; keep the files of the newest few, and of the newest good one.
KEEP_WEB_ARCHIVES = 4
ARCHIVES = Path.home() / "second-look-backups" / "deploys"
WORKER_NAME = "second-look-api"
PAGES_PROJECT = "second-look"
PAGES_HOST = "second-look-79t.pages.dev"
PARTS = ("worker", "web")

VERSION_RE = re.compile(
    r"Current Version ID:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)
PAGES_RE = re.compile(r"https://([0-9a-f]{8})\." + re.escape(PAGES_HOST))


@dataclass(frozen=True)
class Row:
    when: str
    part: str
    commit: str
    id: str
    archive: str
    checked: bool

    def cells(self) -> str:
        archive = f"`{self.archive}`" if self.archive else ""
        return (
            f"| {self.when} | {self.part} | `{self.commit}` | `{self.id}` | {archive} | "
            f"{'yes' if self.checked else 'no'} |"
        )


class RecordError(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def block(text: str) -> tuple[int, int]:
    """Where the rows sit: the character span between the two markers."""
    a, b = text.find(START), text.find(END)
    if a < 0 or b < a:
        raise RecordError(f"docs/notes/hosting.md has no {START} ... {END} block")
    return a + len(START), b


def read_rows(text: str) -> list[Row]:
    a, b = block(text)
    rows = []
    for line in text[a:b].splitlines():
        if not line.startswith("| ") or line in (HEAD, RULE) or line.startswith("| When"):
            continue
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[1] not in PARTS:
            raise RecordError(f"a row in the deploy record cannot be read: {line}")
        rows.append(Row(cells[0], cells[1], cells[2], cells[3], cells[4], cells[5] == "yes"))
    return rows


def write_rows(text: str, rows: list[Row]) -> str:
    a, b = block(text)
    body = "\n".join([HEAD, RULE, *(r.cells() for r in rows[:KEEP_ROWS])])
    return text[:a] + "\n" + body + "\n" + text[b:]


def load(path: Path = HOSTING) -> list[Row]:
    return read_rows(path.read_text(encoding="utf-8"))


def save(rows: list[Row], path: Path = HOSTING) -> None:
    path.write_text(write_rows(path.read_text(encoding="utf-8"), rows), encoding="utf-8")


def worker_version(output: str) -> str:
    m = VERSION_RE.search(output)
    if not m:
        raise RecordError("wrangler deploy printed no Current Version ID")
    return m.group(1)


def pages_deployment(output: str) -> str:
    found = PAGES_RE.findall(output)
    if not found:
        raise RecordError(f"wrangler pages deploy printed no https://<id>.{PAGES_HOST} address")
    return str(found[-1])


def home_path(path: Path) -> str:
    """A path under the home folder written with ~, so no user name lands in the repo."""
    try:
        return "~/" + path.resolve().relative_to(Path.home().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def expand(path: str) -> Path:
    return Path(path).expanduser()


def archive_web(web_dir: Path, archives: Path, commit: str, when: str) -> Path:
    """Keep the files that went up: out/, functions/ and wrangler.jsonc, as Pages read them."""
    dest = archives / f"web-{when.replace(':', '').replace('-', '')}-{commit}"
    dest.mkdir(parents=True, exist_ok=False)
    shutil.copytree(web_dir / "out", dest / "out", symlinks=True)
    if (web_dir / "functions").is_dir():
        shutil.copytree(web_dir / "functions", dest / "functions", symlinks=True)
    shutil.copy2(web_dir / "wrangler.jsonc", dest / "wrangler.jsonc")
    (dest / "COMMIT").write_text(commit + "\n", encoding="utf-8")
    return dest


def prune_archives(rows: list[Row], archives: Path) -> list[Path]:
    """Delete kept site uploads no row still needs; never the newest good one."""
    web = [r for r in rows if r.part == "web" and r.archive]
    keep = {expand(r.archive).resolve() for r in web[:KEEP_WEB_ARCHIVES]}
    good = next((r for r in web if r.checked), None)
    if good:
        keep.add(expand(good.archive).resolve())
    removed = []
    if archives.is_dir():
        for path in sorted(archives.glob("web-*")):
            if path.is_dir() and path.resolve() not in keep:
                shutil.rmtree(path)
                removed.append(path)
    return removed


def record(
    part: str,
    output: str,
    *,
    commit: str,
    when: str,
    hosting: Path = HOSTING,
    web_dir: Path | None = None,
    archives: Path | None = None,
) -> Row:
    archives = archives or ARCHIVES  # read at call time, so a test can point it elsewhere
    rows = load(hosting)
    if part == "worker":
        row = Row(when, part, commit, worker_version(output), "", False)
    else:
        deployment = pages_deployment(output)
        kept = archive_web(web_dir or ROOT / "apps" / "web", archives, commit, when)
        row = Row(when, part, commit, deployment, home_path(kept), False)
    rows.insert(0, row)
    save(rows, hosting)
    # Only a site upload adds an archive, so only a site upload prunes: a Worker deploy never
    # deletes a kept site build (a test that recorded a Worker deploy once emptied the real folder).
    if part == "web":
        prune_archives(rows[:KEEP_ROWS], archives)
    return row


def mark_good(rows: list[Row], commit: str | None = None) -> list[Row]:
    """Mark good the unchecked rows of one commit, by default the newest row's commit."""
    if not rows:
        return rows
    target = commit or rows[0].commit
    return [
        replace(r, checked=True) if (not r.checked and r.commit.startswith(target[:7])) else r
        for r in rows
    ]


# ---------------------------------------------------------------------------
# What is live, read with wrangler (outward, read only)
# ---------------------------------------------------------------------------


def live_worker(out: Outward, root: Path = ROOT) -> str | None:
    done = out.run(
        ["npx", "wrangler", "deployments", "status", "--json", "--name", WORKER_NAME],
        cwd=root / "worker",
        timeout=120,
    )
    if not done.ok:
        return None
    try:
        versions = json.loads(done.out).get("versions") or []
    except (ValueError, AttributeError):
        return None
    full = [v for v in versions if v.get("percentage") == 100]
    return str(full[0]["version_id"]) if full else None


def live_pages(out: Outward, root: Path = ROOT) -> dict[str, str] | None:
    """The newest production deployment: its short id and the commit it says it was built from."""
    done = out.run(
        [
            "npx", "wrangler", "pages", "deployment", "list",
            "--project-name", PAGES_PROJECT, "--environment", "production", "--json",
        ],
        cwd=root / "apps" / "web",
        timeout=120,
    )  # fmt: skip
    if not done.ok:
        return None
    try:
        items = json.loads(done.out)
        first = items[0]
        m = PAGES_RE.search(str(first.get("Deployment", "")))
        return {
            "id": m.group(1) if m else str(first.get("Id", ""))[:8],
            "commit": str(first.get("Source", "")),
        }
    except (ValueError, IndexError, KeyError, TypeError, AttributeError):
        return None


def good_for_live(
    rows: list[Row], worker: str | None, pages: dict[str, str] | None
) -> tuple[Row | None, Row | None, list[str]]:
    """The good rows that describe what is live now, and what is missing."""
    problems = []
    w = next((r for r in rows if r.part == "worker" and r.checked and r.id == worker), None)
    if worker is None:
        problems.append("the live Worker version could not be read with wrangler")
    elif w is None:
        problems.append(f"the live Worker version {worker} is not a good row in the deploy record")
    p = None
    if pages is None:
        problems.append("the live Pages deployment could not be read with wrangler")
    else:
        live_commit = pages["commit"][:7]
        p = next(
            (
                r
                for r in rows
                if r.part == "web"
                and r.checked
                and live_commit
                and r.commit[:7] == live_commit
                and expand(r.archive).is_dir()
            ),
            None,
        )
        if p is None:
            problems.append(
                f"the live Pages build (commit {live_commit or 'unknown'}) is not a good row "
                "with its files kept in the deploy record"
            )
    return w, p, problems


def git_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record", help="add a row after a deploy")
    rec.add_argument("part", choices=PARTS)
    rec.add_argument("--output-file", type=Path, required=True, help="what wrangler printed")
    rec.add_argument("--commit", default=None)
    rec.add_argument("--web-dir", type=Path, default=ROOT / "apps" / "web")
    rec.add_argument("--archives", type=Path, default=ARCHIVES)
    good = sub.add_parser("good", help="mark rows good once the phone tests passed")
    good.add_argument("--commit", default=None)
    sub.add_parser("show")
    sub.add_parser("check-live", help="exit 0 when what is live is a good row")
    args = parser.parse_args(argv)

    try:
        if args.command == "record":
            commit = args.commit or git_commit(ROOT)
            row = record(
                args.part,
                args.output_file.read_text(encoding="utf-8", errors="replace"),
                commit=commit,
                when=now_utc(),
                web_dir=args.web_dir,
                archives=args.archives,
            )
            print(f"deploy-record: {row.part} {row.id} at {row.commit} recorded, not yet checked")
            return 0
        rows = load()
        if args.command == "good":
            marked = mark_good(rows, args.commit)
            save(marked)
            n = sum(1 for a, b in zip(rows, marked, strict=True) if a != b)
            print(f"deploy-record: {n} row(s) marked good")
            return 0 if n else 1
        if args.command == "show":
            print("\n".join(r.cells() for r in rows) or "deploy-record: no rows yet")
            return 0
        out = Outward()
        w, p, problems = good_for_live(rows, live_worker(out), live_pages(out))
        for line in problems:
            print(f"deploy-record: {line}")
        if problems:
            return 1
        assert w is not None and p is not None
        print(f"deploy-record: live Worker {w.id} and Pages {p.id} ({p.commit}) are good rows")
        return 0
    except RecordError as e:
        print(f"deploy-record: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
