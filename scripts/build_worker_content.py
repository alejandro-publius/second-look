"""Write the content the API Worker needs into worker/src/content.json.

The gold key lives here. It never reaches the browser: apps/web/scripts/build-content.mjs strips
it, and this file is bundled into the Worker only. One source, content/, two consumers.
"""

from __future__ import annotations

import json
from pathlib import Path

from apps.api import content

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "worker" / "src" / "content.json"


def main() -> int:
    loaded = content.get_content()
    items = [
        {"id": item["id"], "feature": item["feature"], "gold": item["gold"]}
        for item in loaded.test_items
    ]
    doc = {
        "content_hash": loaded.content_hash(),
        "features": sorted({item["feature"] for item in items}),
        "test_items": items,
        "warmup_ids": sorted(content.warmup_ids()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"build-worker-content: {len(items)} test items into {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
