"""Compare two labellers' files, report Cohen's kappa, list every disagreement, apply when clean.

Run: uv run python scripts/merge_labels.py labels_rachel.csv labels_alex.csv [--apply]
Writes results/key_agreement.json (kappa per feature and overall, every disagreement, every
ambiguous label). Prints each disagreement with the photo id and both labels. With --apply it
writes gold_label and labeller_2 into photos/manifest.csv, but only when no disagreement and no
ambiguous label remains; otherwise it refuses and says how many are left.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.records import FEATURES

ROOT = Path(__file__).resolve().parents[1]


class MergeError(Exception):
    """Bad input. Nothing was written."""


def labeller_name(path: Path) -> str:
    stem = path.stem
    return stem[len("labels_") :] if stem.startswith("labels_") else stem


def read_labels(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise MergeError(f"labels file not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        needed = {"photo_id", "feature", "label"}
        if not needed <= set(reader.fieldnames or []):
            raise MergeError(f"{path.name} needs columns photo_id, feature, label")
        rows = {r["photo_id"]: dict(r) for r in reader if r.get("photo_id")}
    for pid, row in rows.items():
        if row["label"] not in {"present", "absent", "ambiguous"}:
            raise MergeError(f"{path.name}: {pid} has label {row['label']!r}")
    return rows


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa over (label_a, label_b) pairs. None with no pairs.

    When both people used a single category for everything, chance agreement is 1 and kappa is
    undefined; we report 1.0 for full agreement and 0.0 otherwise and say so in the file.
    """
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return round((po - pe) / (1 - pe), 4)


def compare(a: dict[str, dict[str, str]], b: dict[str, dict[str, str]]) -> dict[str, Any]:
    common = sorted(set(a) & set(b))
    disagreements: list[dict[str, str]] = []
    ambiguous: list[dict[str, str]] = []
    pairs_by_feature: dict[str, list[tuple[str, str]]] = {f: [] for f in FEATURES}
    for pid in common:
        if a[pid]["feature"] != b[pid]["feature"]:
            raise MergeError(
                f"{pid}: the two files name different features "
                f"({a[pid]['feature']} and {b[pid]['feature']}); the manifest changed between them"
            )
        feature = a[pid]["feature"]
        la, lb = a[pid]["label"], b[pid]["label"]
        pairs_by_feature.setdefault(feature, []).append((la, lb))
        entry = {"photo_id": pid, "feature": feature, "a": la, "b": lb}
        if la != lb:
            disagreements.append(entry)
        if "ambiguous" in (la, lb):
            ambiguous.append(entry)
    per_feature = {
        f: {
            "n": len(pairs),
            "agree": sum(1 for x, y in pairs if x == y),
            "kappa": cohen_kappa(pairs),
        }
        for f, pairs in pairs_by_feature.items()
    }
    all_pairs = [p for pairs in pairs_by_feature.values() for p in pairs]
    return {
        "n_common": len(common),
        "only_in_a": sorted(set(a) - set(b)),
        "only_in_b": sorted(set(b) - set(a)),
        "per_feature": per_feature,
        "overall": {
            "n": len(all_pairs),
            "agree": sum(1 for x, y in all_pairs if x == y),
            "kappa": cohen_kappa(all_pairs),
        },
        "disagreements": disagreements,
        "ambiguous": ambiguous,
    }


def apply_to_manifest(
    manifest: Path, a: dict[str, dict[str, str]], b: dict[str, dict[str, str]], common: list[str]
) -> int:
    with manifest.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    if "gold_label" not in columns or "labeller_2" not in columns:
        raise MergeError("manifest lacks gold_label or labeller_2 columns")
    wanted = set(common)
    applied = 0
    for row in rows:
        if row["id"] in wanted:
            row["gold_label"] = a[row["id"]]["label"]
            row["labeller_2"] = b[row["id"]]["label"]
            applied += 1
    with manifest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file_a", type=Path)
    parser.add_argument("file_b", type=Path)
    parser.add_argument("--apply", action="store_true", help="write into photos/manifest.csv")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--out", type=Path, default=None, help="default results/key_agreement.json")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    out = args.out or (root / "results" / "key_agreement.json")
    try:
        a, b = read_labels(args.file_a), read_labels(args.file_b)
        name_a, name_b = labeller_name(args.file_a), labeller_name(args.file_b)
        result = compare(a, b)
    except MergeError as e:
        print(f"merge: refused: {e}")
        return 1

    for d in result["disagreements"]:
        print(f"disagree   {d['photo_id']}  {d['feature']}  {name_a}={d['a']}  {name_b}={d['b']}")
    for d in result["ambiguous"]:
        if d["a"] == d["b"]:
            print(f"ambiguous  {d['photo_id']}  {d['feature']}  both said ambiguous")
    for pid in result["only_in_a"]:
        print(f"unmatched  {pid}  labelled by {name_a} only")
    for pid in result["only_in_b"]:
        print(f"unmatched  {pid}  labelled by {name_b} only")
    for f, stats in result["per_feature"].items():
        print(
            f"kappa      {f:16} n={stats['n']:3}  agree={stats['agree']:3}  kappa={stats['kappa']}"
        )
    o = result["overall"]
    print(f"kappa      {'overall':16} n={o['n']:3}  agree={o['agree']:3}  kappa={o['kappa']}")

    n_dis, n_amb = len(result["disagreements"]), len(result["ambiguous"])
    applied = 0
    clean = n_dis == 0 and n_amb == 0
    if args.apply:
        if not clean:
            print(
                f"merge: refusing to apply: {n_dis} disagreements and {n_amb} ambiguous labels "
                "remain; settle them, relabel, and run again"
            )
        else:
            common = sorted(set(a) & set(b))
            try:
                applied = apply_to_manifest(root / "photos" / "manifest.csv", a, b, common)
            except MergeError as e:
                print(f"merge: refused: {e}")
                return 1
            print(f"merge: applied {applied} labels to photos/manifest.csv (labeller_2 = {name_b})")

    payload = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "scripts/merge_labels.py",
        "synthetic": False,
        "labellers": [name_a, name_b],
        "kappa_note": "Cohen's kappa; 1.0 or 0.0 when both used one category for every photo",
        **result,
        "applied": applied,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"merge: {result['n_common']} photos in common, {n_dis} disagreements, {n_amb} ambiguous")
    print(f"merge: wrote {out.relative_to(root) if out.is_relative_to(root) else out}")
    return 0 if (clean or not args.apply) else 1


if __name__ == "__main__":
    sys.exit(main())
