"""Make the repository public, on Sep 30, in the one safe order (Update 14 section 8 item 2).

    make go-public            says what it would do and changes nothing
    make go-public GO=yes     does it: Alex runs this, on main, on Sep 30

What it does, in order, stopping at the first thing that is wrong:

1. Refuses unless it is on main with a clean tree.
2. `git rm -r docs/internal`: the working notes between the team and their AI coding tools.
3. Rewrites every mention of docs/internal left in a tracked file to "the team's working notes",
   so no page points at a folder that is gone. Nothing reads a file there; every mention is a
   comment or a sentence, which the dry run lists.
4. Runs `make submit-check` and reads its "submit-check: N failed: ..." line. The only failure it
   accepts is the repository not yet being public, which is the next step. Any other failure, or
   no such line at all (a crash), stops the run before anything is published.
5. Commits, pushes, and only then runs `gh repo edit --visibility public`.

The commit removes the working notes from the tip only. Git history still holds docs/internal,
and this script never rewrites history (hard rule 15).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERNAL = "docs/internal"
GITLEAKS_CONFIG = ".gitleaks.toml"
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
# A mention ends at a space, a stop, a bracket or a double quote; the quote covers JSON strings
# in results/, such as the link check's targets.
MENTION = re.compile(
    r"`?docs/internal(?:/(?:(?:updates|reports|reviews|upstream)/)?(?P<name>[A-Za-z0-9_.-]+?)?(?:\.md)?/?)?`?"
    r"(?=[\s,.;:)\"]|$)"
)
ALLOWED_SUBMIT_FAILURES = {"repo_public"}
SUBMIT_SUMMARY = re.compile(r"^submit-check: (\d+) failed: (.*)$", re.MULTILINE)
COMMIT_MESSAGE = "Open the repository: remove the working notes from the tip; history keeps them"


def rewrite(text: str) -> str:
    """Every mention of the folder becomes a plain phrase that points nowhere."""
    text = README_LINE.sub("", text)

    def named(m: re.Match[str]) -> str:
        name = (m.group("name") or "").replace("_", " ").strip()
        return f"the team's working notes ({name})" if name else "the team's working notes"

    return MENTION.sub(named, text)


def run_parts(cmd: list[str]) -> tuple[int, str, str]:
    """The exit code, stdout and stderr, kept apart."""
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def run(cmd: list[str]) -> tuple[int, str]:
    code, out, err = run_parts(cmd)
    return code, (out + err).strip()


def mentions() -> list[tuple[str, int]]:
    # This script and its test name the folder on purpose. So does .gitleaks.toml: gitleaks reads
    # the whole history, which keeps the folder after this run, so its allowlist for the review
    # patch files there has to keep the real path.
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
            f":!{GITLEAKS_CONFIG}",
        ]
    )
    rows = []
    for line in out.splitlines() if code == 0 else []:
        path, _, count = line.rpartition(":")
        rows.append((path, int(count)))
    return rows


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
    failed = submit_failures(stdout)
    if failed is None:
        return "submit-check printed no summary line it could read (did it crash?)"
    others = failed - ALLOWED_SUBMIT_FAILURES
    if others:
        return f"submit-check failed on {sorted(others)}"
    if code != 0 and not failed:
        return f"submit-check exited {code} but named no failed check"
    return None


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
        print(f"     (from the tip only: the git history still holds {INTERNAL})")
        print(f"  3. rewrite {sum(c for _, c in rows)} mentions in {len(rows)} files:")
        for path, count in rows:
            print(f"       {path}: {count}")
        print("  4. run make submit-check; stop on anything but the repo not being public yet,")
        print("     and stop if it prints no summary line")
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
    code, out, err = run_parts(["make", "submit-check"])
    blocker = submit_blocker(code, out)
    if blocker:
        print((out + err).strip())
        print(f"go-public: stopped before publishing; {blocker}")
        return 1
    for cmd in (
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", COMMIT_MESSAGE],
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
