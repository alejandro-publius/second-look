"""Freeze the gold key: write results/key_hash.json and log key_frozen in the audit log.

Run: uv run python scripts/freeze_key.py
The hash is sha256 of the JSON list of sorted (item_id, gold) pairs from content/test_items.yaml.
It refuses while any test photo is a placeholder or lacks a second label, unless
--allow-placeholders is given for the synthetic dry run; the file then says placeholders true
and preflight keeps failing on it.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from scripts import audit_log

ROOT = Path(__file__).resolve().parents[1]


class FreezeError(Exception):
    """Refused. Nothing was written."""


def load_items(root: Path) -> list[dict[str, Any]]:
    with (root / "content" / "test_items.yaml").open(encoding="utf-8") as f:
        items = yaml.safe_load(f).get("items", [])
    return [dict(i) for i in items]


def key_hash(items: list[dict[str, Any]]) -> str:
    pairs = sorted((str(i["id"]), str(i["gold"])) for i in items)
    return hashlib.sha256(json.dumps(pairs, separators=(",", ":")).encode()).hexdigest()


def placeholder_problems(root: Path, items: list[dict[str, Any]]) -> list[str]:
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        photos = {r["id"]: r for r in csv.DictReader(f)}
    problems: list[str] = []
    for item in items:
        photo = photos.get(str(item.get("photo_id")))
        if photo is None:
            problems.append(f"item {item.get('id')}: photo {item.get('photo_id')} not in manifest")
            continue
        if photo["license"] == "placeholder":
            problems.append(f"item {item['id']}: photo {photo['id']} is a placeholder")
        if not photo.get("labeller_2", "").strip():
            problems.append(f"item {item['id']}: photo {photo['id']} has no second label")
        if photo.get("gold_label") != item.get("gold"):
            problems.append(
                f"item {item['id']}: gold {item.get('gold')} disagrees with manifest "
                f"{photo.get('gold_label')!r}"
            )
    return problems


def freeze(root: Path, *, allow_placeholders: bool = False) -> dict[str, Any]:
    root = root.resolve()
    items = load_items(root)
    if not items:
        raise FreezeError("content/test_items.yaml has no items")
    problems = placeholder_problems(root, items)
    disagreements = [p for p in problems if "disagrees" in p]
    if disagreements:
        raise FreezeError("\n".join(disagreements))
    if problems and not allow_placeholders:
        raise FreezeError(
            "\n".join(problems) + "\n(pass --allow-placeholders only for the synthetic dry run)"
        )
    placeholders = bool(problems)
    digest = key_hash(items)
    record: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "scripts/freeze_key.py",
        "synthetic": placeholders,
        "key_sha256": digest,
        "n_items": len(items),
        "placeholders": placeholders,
        "hash_of": "sha256 of the JSON list of sorted [item_id, gold] pairs",
    }
    if placeholders:
        record["stamp"] = "SYNTHETIC"
        record["placeholder_problems"] = problems
    audit_hash = audit_log.append(
        "key_frozen",
        {"key_sha256": digest, "n_items": len(items), "placeholders": placeholders},
        path=root / "audit" / "log.jsonl",
    )
    record["audit_hash"] = audit_hash
    out = root / "results" / "key_hash.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--allow-placeholders", action="store_true", help="synthetic dry run only")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        record = freeze(args.root, allow_placeholders=args.allow_placeholders)
    except FreezeError as e:
        print("freeze-key: refused, nothing written:")
        print(e)
        return 1
    print(
        f"freeze-key: {record['n_items']} items, key sha256 {record['key_sha256']}, "
        f"placeholders {str(record['placeholders']).lower()}, audit hash {record['audit_hash']}"
    )
    if record["placeholders"]:
        print("freeze-key: this key is SYNTHETIC; preflight will fail until real labels land")
    return 0


if __name__ == "__main__":
    sys.exit(main())
