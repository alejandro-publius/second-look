"""The answer key in content/test_items.yaml is the one that was frozen (docs/THREAT_MODEL.md).

scripts/freeze_key.py hashed the 16 gold labels into results/key_hash.json and wrote the moment
to the audit log. make preflight compares the two, but it is not part of make check, so a quiet
edit to one gold label, by a person or by a coding agent, would pass every other test and move
every score and every model result. This test runs in make check.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import freeze_key

ROOT = Path(__file__).resolve().parents[2]


def test_the_answer_key_is_the_one_that_was_frozen() -> None:
    record = json.loads((ROOT / "results" / "key_hash.json").read_text(encoding="utf-8"))
    items = freeze_key.load_items(ROOT)
    assert len(items) == record["n_items"] == 16
    assert freeze_key.key_hash(items) == record["key_sha256"], (
        "content/test_items.yaml changed after the key was frozen; a change to the key is a "
        "deviation (docs/deviations.md) and needs scripts/freeze_key.py again"
    )
    assert record["placeholders"] is False and record["synthetic"] is False
