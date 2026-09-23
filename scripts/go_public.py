"""Make the repository public, on Sep 30, in the one safe order (Update 14 section 8 item 2).

    make go-public            says what it would do and changes nothing
    make go-public GO=yes     does it: Alex runs this, on main, on Sep 30

What it does, in order, stopping at the first thing that is wrong:

1. Refuses unless it is on main with a clean tree.
2. `git rm -r docs/internal`: the working notes between the team and their AI coding tools.
3. Rewrites every mention of docs/internal left in a tracked file to "the team's working notes",
   so no page points at a folder that is gone. Nothing reads a file there; every mention is a
   comment or a sentence, which the dry run lists.
4. Runs `make submit-check`. The only failure it accepts is the repository not yet being public,
   which is the next step. Anything else stops the run before anything is published.
5. Commits, pushes, and only then runs `gh repo edit --visibility public`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERNAL = "docs/internal"
PUBLIC_CMD = [
    "gh",
    "repo",
    "edit",
    "alejandro-publius/second-look",
    "--visibility",
    "public",
    "--accept-visibility-change-consequences",
]
# The one line in the README that talks about the folder itself goes, rather than being reworded.
README_LINE = re.compile(r"; docs/internal/ holds the working notes, removed before the repo opens")
MENTION = re.compile(
    r"`?docs/internal(?:/(?:(?:updates|reports|reviews)/)?(?P<name>[A-Za-z0-9_.-]+?)?(?:\.md)?/?)?`?"
    r"(?=[\s,.;:)]|$)"
)
ALLOWED_SUBMIT_FAILURES = {"repo_public"}


def rewrite(text: str) -> str:
    """Every mention of the folder becomes a plain phrase that points nowhere."""
    text = README_LINE.sub("", text)

    def named(m: re.Match[str]) -> str:
        name = (m.group("name") or "").replace("_", " ").strip()
        return f"the team's working notes ({name})" if name else "the team's working notes"

    return MENTION.sub(named, text)


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def mentions() -> list[tuple[str, int]]:
    # This script and its test name the folder on purpose, and are the one place that may.
    code, out = run(
        [
            "git",
            "grep",
            "-c",
            INTERNAL,
            "--",
            ".",
            f":!{INTERNAL}",
            ":!scripts/go_public.py",
            ":!scripts/tests/test_go_public.py",
        ]
    )
    rows = []
    for line in out.splitlines() if code == 0 else []:
        path, _, count = line.rpartition(":")
        rows.append((path, int(count)))
    return rows


def submit_failures(output: str) -> set[str]:
    """The names after "submit-check: N failed:" in its last line, or an empty set."""
    m = re.search(
        r"submit-check: \d+ failed: (.+)$", output.strip().splitlines()[-1] if output else ""
    )
    return {n.strip() for n in m.group(1).split(",")} if m else set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--yes", action="store_true", help="do it, instead of saying what it would do"
    )
    args = parser.parse_args(argv)

    rows = mentions()
    if not args.yes:
        print("go-public: dry run, nothing changes. With GO=yes it would:")
        print("  1. check it is on main with a clean tree")
        print(f"  2. git rm -r {INTERNAL}")
        print(f"  3. rewrite {sum(c for _, c in rows)} mentions in {len(rows)} files:")
        for path, count in rows:
            print(f"       {path}: {count}")
        print("  4. run make submit-check; stop on anything but the repo not being public yet")
        print("  5. commit, push, then: " + " ".join(PUBLIC_CMD))
        return 0

    code, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch != "main":
        print(f"go-public: refused, this is {branch}, not main")
        return 1
    code, status = run(["git", "status", "--porcelain"])
    if status:
        print("go-public: refused, the tree is not clean:\n" + status)
        return 1
    code, out = run(["git", "rm", "-r", "-q", INTERNAL])
    if code != 0:
        print(f"go-public: git rm failed: {out}")
        return 1
    for path, _ in rows:
        file = ROOT / path
        file.write_text(rewrite(file.read_text(encoding="utf-8")), encoding="utf-8")
    left = mentions()
    if left:
        print(f"go-public: stopped, mentions left after the rewrite: {left}")
        return 1
    code, out = run(["make", "submit-check"])
    failed = submit_failures(out)
    if code != 0 and not failed <= ALLOWED_SUBMIT_FAILURES:
        print(out)
        print(f"go-public: stopped before publishing; submit-check failed on {sorted(failed)}")
        return 1
    for cmd in (
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "Open the repository: the working notes stay private"],
        ["git", "push", "-q", "origin", "main"],
        PUBLIC_CMD,
    ):
        code, out = run(cmd)
        if code != 0:
            print(f"go-public: {' '.join(cmd)} failed: {out}")
            return 1
    print("go-public: the repository is public")
    return 0


if __name__ == "__main__":
    sys.exit(main())
