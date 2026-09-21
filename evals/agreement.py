"""Cohen's kappa per feature between two labellers (analysis plan item 3, master brief section 10).

Default input: photos/manifest.csv, columns gold_label and labeller_2, on rows with a feature and
role test or benchmark. Or two CSV files with columns id, feature, label, joined on id:
    uv run python evals/agreement.py --a labels_rachel.csv --b labels_alex.csv

Writes results/agreement_<stamp>.json. When a column is empty it says so in one plain sentence
and writes null for kappa instead of a number.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from core.records import FEATURES
from evals.model_sweep import DEFAULT_RESULTS, load_manifest, now_utc, stamp, write_json

SCRIPT = "evals/agreement.py"
POOL_ROLES = frozenset({"benchmark", "test"})
Pair = tuple[str, str]


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Kappa over any set of categories. None when there are no pairs or chance agreement is 1."""
    if len(a) != len(b):
        raise ValueError("the two label lists differ in length")
    n = len(a)
    if n == 0:
        return None
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    count_a = Counter(a)
    count_b = Counter(b)
    expected = sum(count_a[c] * count_b[c] for c in set(a) | set(b)) / (n * n)
    if expected >= 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def _feature_pairs(
    rows: Iterable[tuple[str, str, str]],
) -> tuple[dict[str, list[Pair]], dict[str, int], dict[str, int]]:
    """rows of (feature, label_a, label_b) into pairs per feature plus counts of empties."""
    pairs: dict[str, list[Pair]] = {f: [] for f in FEATURES}
    missing_a: dict[str, int] = {f: 0 for f in FEATURES}
    missing_b: dict[str, int] = {f: 0 for f in FEATURES}
    for feature, a, b in rows:
        if feature not in pairs:
            continue
        a, b = a.strip(), b.strip()
        if not a:
            missing_a[feature] += 1
        if not b:
            missing_b[feature] += 1
        if a and b:
            pairs[feature].append((a, b))
    return pairs, missing_a, missing_b


def pairs_from_manifest(
    manifest: Mapping[str, Mapping[str, str]],
    *,
    col_a: str = "gold_label",
    col_b: str = "labeller_2",
) -> tuple[dict[str, list[Pair]], dict[str, int], dict[str, int], int]:
    rows = [
        (row.get("feature", ""), row.get(col_a, ""), row.get(col_b, ""))
        for row in manifest.values()
        if row.get("role") in POOL_ROLES and row.get("feature") in FEATURES
    ]
    pairs, ma, mb = _feature_pairs(rows)
    placeholders = sum(
        1
        for row in manifest.values()
        if row.get("role") in POOL_ROLES and row.get("license") == "placeholder"
    )
    return pairs, ma, mb, placeholders


def _read_labels(path: Path) -> dict[str, tuple[str, str]]:
    """id to (feature, label) from a CSV with columns id, feature, label."""
    out: dict[str, tuple[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["id"]] = (row.get("feature", ""), row.get("label", ""))
    return out


def pairs_from_csvs(
    path_a: Path, path_b: Path
) -> tuple[dict[str, list[Pair]], dict[str, int], dict[str, int]]:
    a = _read_labels(path_a)
    b = _read_labels(path_b)
    rows = []
    for photo_id in sorted(set(a) | set(b)):
        fa, la = a.get(photo_id, ("", ""))
        fb, lb = b.get(photo_id, ("", ""))
        rows.append((fa or fb, la, lb))
    return _feature_pairs(rows)


def summarise(
    pairs: Mapping[str, Sequence[Pair]],
    missing_a: Mapping[str, int],
    missing_b: Mapping[str, int],
    *,
    name_a: str,
    name_b: str,
) -> tuple[dict[str, Any], str]:
    """Per feature kappa and a one sentence plain reading of the whole thing."""
    features: dict[str, Any] = {}
    all_pairs: list[Pair] = []
    for feature in FEATURES:
        ps = list(pairs.get(feature, []))
        all_pairs.extend(ps)
        kappa = cohens_kappa([p[0] for p in ps], [p[1] for p in ps])
        agree = sum(1 for x, y in ps if x == y)
        if not ps:
            note = f"no photo of {feature} has both labels yet"
        elif kappa is None:
            note = "every label is the same category, so kappa is undefined"
        else:
            note = ""
        features[feature] = {
            "n_pairs": len(ps),
            "agree": agree,
            "agreement_share": round(agree / len(ps), 4) if ps else None,
            "kappa": None if kappa is None else round(kappa, 4),
            f"missing_{name_a}": missing_a.get(feature, 0),
            f"missing_{name_b}": missing_b.get(feature, 0),
            "note": note,
        }
    total_missing_b = sum(missing_b.values())
    total_missing_a = sum(missing_a.values())
    if not all_pairs:
        if total_missing_b and not total_missing_a:
            sentence = (
                f"The {name_b} column is empty for every photo, "
                "so there is no agreement to compute yet."
            )
        elif total_missing_a and not total_missing_b:
            sentence = (
                f"The {name_a} column is empty for every photo, "
                "so there is no agreement to compute yet."
            )
        else:
            sentence = "No photo has both labels yet, so there is no agreement to compute."
    else:
        overall = cohens_kappa([p[0] for p in all_pairs], [p[1] for p in all_pairs])
        k = "undefined" if overall is None else f"{overall:.2f}"
        sentence = f"Kappa over all {len(all_pairs)} double labelled photos is {k}."
    return features, sentence


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--a", type=Path, default=None, help="first labeller CSV: id, feature, label")
    p.add_argument("--b", type=Path, default=None, help="second labeller CSV: id, feature, label")
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if (args.a is None) != (args.b is None):
        print("Give both --a and --b, or neither to read photos/manifest.csv.")
        return 2
    if args.a is not None and args.b is not None:
        pairs, ma, mb = pairs_from_csvs(args.a, args.b)
        name_a, name_b = args.a.stem, args.b.stem
        source: dict[str, Any] = {"a": str(args.a), "b": str(args.b)}
        placeholders = 0
    else:
        pairs, ma, mb, placeholders = pairs_from_manifest(load_manifest())
        name_a, name_b = "gold_label", "labeller_2"
        source = {"manifest": "photos/manifest.csv", "columns": [name_a, name_b]}
    features, sentence = summarise(pairs, ma, mb, name_a=name_a, name_b=name_b)
    synthetic = placeholders > 0
    doc: dict[str, Any] = {
        "generated_at_utc": now_utc(),
        "script": SCRIPT,
        "synthetic": synthetic,
        "source": source,
        "n_placeholders_in_pool": placeholders,
        "features": features,
        "sentence": sentence,
    }
    if synthetic:
        doc["stamp"] = "SYNTHETIC"
        doc["placeholder_note"] = (
            "The pool still holds gray placeholders, so any label here is a stand-in."
        )
    out = args.results_dir / f"agreement_{stamp()}.json"
    write_json(out, doc)
    print(sentence)
    for feature, cell in features.items():
        k = "undefined" if cell["kappa"] is None else f"{cell['kappa']:.2f}"
        tail = f", {cell['note']}" if cell["note"] else ""
        print(f"  {feature}: {cell['n_pairs']} pairs, kappa {k}{tail}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
