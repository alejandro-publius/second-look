"""Fetch every photo in the picks files, one a second, and print what landed and what did not.

Run: uv run python scripts/batch_fetch_photos.py            all picks-*.csv under photos/candidates
     uv run python scripts/batch_fetch_photos.py --dry-run  check the sources, download nothing

In: photos/candidates/picks-<feature>.csv, the file the contact sheet writes, with columns
url, feature, role, side, scene, notes. Two columns this script adds: label, the label the
person chose while picking, and evidence, anything the picker can support from the source.
Out: one ingested photo per row and one manifest row, through scripts/fetch_open_photo.py, so
there is still only one ingest path and one licence check.

A row with role spare is not fetched. It waits, and stands in for a row of the same feature and
label whose fetch failed (Update 11b step 3). Every swap is printed and every refusal is printed
with its reason. Nothing is guessed: a photo that cannot be recorded is left out.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import httpx

from scripts.fetch_open_photo import FetchError, fetch
from scripts.find_open_photos import ROOT, USER_AGENT, RateLimit
from scripts.ingest_photos import GOLD_VALUES, IngestError

PICK_COLUMNS = ["url", "feature", "role", "side", "scene", "notes"]
SPARE = "spare"
# What the launch needs, per feature. The warm-up pair is counted on its own.
TARGETS = {"test": 4, "lesson": 4, "practice": 1}
WARMUP_TARGET = 2
# Short, readable manifest ids: ph-bank-01 rather than ph-open-27.
BATCHES = {
    "artificial_bank": "bank",
    "dug_out_channel": "channel",
    "invasive_plant": "plant",
    "pipe_running": "pipe",
    "warmup": "warmup",
}


class PicksError(Exception):
    """The picks files do not say what to fetch. Nothing was downloaded."""


def read_picks(folder: Path) -> list[dict[str, str]]:
    """Every picks-*.csv in the folder, in feature then file order."""
    files = sorted(folder.glob("picks-*.csv"))
    if not files:
        raise PicksError(f"no picks-*.csv under {folder}")
    rows: list[dict[str, str]] = []
    for path in files:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing = [c for c in PICK_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise PicksError(f"{path.name} is missing columns: {missing}")
            for n, row in enumerate(reader, 2):
                clean = {k: (v or "").strip() for k, v in row.items() if k}
                clean["_where"] = f"{path.name} row {n}"
                label = clean.get("label", "")
                if clean["role"] != SPARE and label not in GOLD_VALUES:
                    raise PicksError(
                        f"{clean['_where']}: label {label!r} must be one of {sorted(GOLD_VALUES)}"
                    )
                rows.append(clean)
    return rows


def spares_for(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    out: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        if row["role"] == SPARE:
            out.setdefault((row["feature"], row.get("label", "")), []).append(row)
    return out


def one(
    row: dict[str, str],
    role: str,
    label: str,
    root: Path,
    client: httpx.Client,
    limiter: RateLimit,
) -> dict[str, str]:
    feature = row["feature"]
    return fetch(
        row["url"],
        feature,
        role,
        batch=BATCHES.get(feature, "open"),
        scene=row.get("scene", ""),
        notes=row.get("notes", ""),
        extra_evidence=row.get("evidence", ""),
        # The warm-up pair is not a feature question, so it carries no gold label.
        gold_label="" if feature == "warmup" else label,
        root=root,
        client=client,
        limiter=limiter,
    )


def table(done: list[dict[str, str]], refused: list[tuple[dict[str, str], str]]) -> list[str]:
    """Feature by role, picked against target, then every refusal with its reason."""
    got: Counter[tuple[str, str]] = Counter((d["feature"] or "warmup", d["role"]) for d in done)
    lines = ["feature          role      picked  target"]
    features = ({f for f, _ in got} | set(BATCHES)) - {"warmup"}
    for feature in sorted(features):
        for role, want in TARGETS.items():
            n = got[(feature, role)]
            mark = "" if n == want else "   <- short" if n < want else "   <- over"
            lines.append(f"{feature:16} {role:9} {n:6}  {want:6}{mark}")
    n = got[("warmup", "warmup")]
    mark = "" if n == WARMUP_TARGET else "   <- short" if n < WARMUP_TARGET else "   <- over"
    lines.append(f"{'warmup':16} {'warmup':9} {n:6}  {WARMUP_TARGET:6}{mark}")
    lines.append("")
    if refused:
        lines.append(f"refused ({len(refused)}):")
        for row, why in refused:
            lines.append(f"  {row['_where']} {row['feature']}/{row['role']}: {why}")
    else:
        lines.append("refused (0): none")
    return lines


def run(folder: Path, root: Path = ROOT, dry_run: bool = False) -> int:
    rows = read_picks(folder)
    spares = spares_for(rows)
    wanted = [r for r in rows if r["role"] != SPARE]
    print(f"batch-fetch: {len(wanted)} to fetch, {sum(len(v) for v in spares.values())} spare(s)")
    if dry_run:
        for row in wanted:
            where = f"{row['feature']}/{row['role']}/{row.get('label', '')}"
            print(f"  would fetch {where} {row['url']}")
        return 0
    done: list[dict[str, str]] = []
    refused: list[tuple[dict[str, str], str]] = []
    swapped: list[str] = []
    limiter = RateLimit()
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for row in wanted:
            label = row.get("label", "")
            try:
                got = one(row, row["role"], label, root, client, limiter)
            except (FetchError, IngestError, httpx.HTTPError) as first:
                stand_in = None
                while spares.get((row["feature"], label)):
                    candidate = spares[(row["feature"], label)].pop(0)
                    try:
                        got = one(candidate, row["role"], label, root, client, limiter)
                    except (FetchError, IngestError, httpx.HTTPError) as second:
                        refused.append((candidate, f"spare also refused: {second}"))
                        continue
                    stand_in = candidate
                    break
                refused.append((row, str(first).replace("\n", " ")))
                if stand_in is None:
                    continue
                swapped.append(
                    f"  {row['feature']}/{row['role']}/{label}: {row['url']} -> {stand_in['url']}"
                )
            done.append(got)
            print(f"  {got['id']:18} {got['role']:9} {got['gold_label'] or '-':8} {got['file']}")
    print()
    if swapped:
        print(f"swapped in a spare ({len(swapped)}):")
        print("\n".join(swapped))
        print()
    print("\n".join(table(done, refused)))
    return 1 if refused else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--folder", type=Path, default=None, help="where the picks files are")
    parser.add_argument("--dry-run", action="store_true", help="list what it would fetch")
    args = parser.parse_args(argv)
    folder = args.folder or args.root / "photos" / "candidates"
    try:
        return run(folder, args.root, args.dry_run)
    except PicksError as e:
        print(f"batch-fetch: refused, nothing written: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
