"""Fail if any tracked text file contains an em dash or an en dash (hard rule 18)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BAD = {chr(0x2014): "em dash", chr(0x2013): "en dash"}  # built from code points on purpose
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".jar",
    ".woff",
    ".woff2",
    ".zip",
}


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True).stdout
    return [Path(p) for p in out.decode().split("\0") if p]


def main() -> int:
    hits: list[str] = []
    for path in tracked_files():
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for ch, name in BAD.items():
                if ch in line:
                    hits.append(f"{path}:{lineno}: {name}")
    if hits:
        print("\n".join(hits))
        print(f"dash-check: {len(hits)} hit(s)")
        return 1
    print("dash-check: no em or en dashes in tracked files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
