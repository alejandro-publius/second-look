"""How the panel study is doing: completed sessions by source and by arm, from the live counts.

Reads only the public counts endpoint, the same one the site shows; test sessions are never in it.

  uv run python scripts/panel_status.py            the live site
  SITE_URL=http://localhost:3100 uv run python scripts/panel_status.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Any

SITE = "https://second-look-79t.pages.dev"
TARGET = 80


def render(counts: dict[str, Any]) -> str:
    by_source = counts.get("by_source") or {}
    by_arm = counts.get("by_arm") or {}
    lines = ["Completed sessions by source:"]
    lines += [f"  {name:<12} {n}" for name, n in sorted(by_source.items())]
    lines.append("By arm (randomized, completed):")
    lines += [
        f"  {arm:<12} {v.get('randomized', 0)}, {v.get('completed', 0)}"
        for arm, v in sorted(by_arm.items())
    ]
    panel = int(by_source.get("panel", 0))
    lines.append(f"Panel: {panel} of the {TARGET} completed sessions the study asks for.")
    return "\n".join(lines)


def main() -> int:
    site = os.environ.get("SITE_URL", SITE).rstrip("/")
    try:
        req = urllib.request.Request(
            f"{site}/api/test/counts", headers={"User-Agent": "second-look-panel-status"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            counts = json.load(r)
    except OSError as e:
        print(f"panel-status: could not read {site}/api/test/counts: {e}")
        return 1
    print(render(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
