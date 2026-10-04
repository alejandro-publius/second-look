"""Keep a de-identified part 2 export, then clear only its two raw tables.

The Mac runs this once on November 30, 2026 at 09:00 Pacific, or on wake after it.
An early call does nothing. A completion receipt prevents another deletion next year.
Run without --execute to inspect the plan without accessing D1.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.study_export import part2_export_texts

ROOT = Path(__file__).resolve().parents[1]
DELETE_AT = datetime(2026, 11, 30, 17, tzinfo=UTC)
ARCHIVES = Path.home() / "second-look-backups" / "part2-retention"
DELETE_SQL = "DELETE FROM part2_response; DELETE FROM part2_session;"
Query = Callable[[str], list[dict[str, Any]]]


def d1(sql: str) -> list[dict[str, Any]]:
    proc = subprocess.run(
        [
            "npx",
            "--no-install",
            "wrangler",
            "d1",
            "execute",
            "second-look",
            "--remote",
            "--json",
            "--command",
            sql,
        ],
        cwd=ROOT / "worker",
        capture_output=True,
        text=True,
        timeout=180,
        check=True,
    )
    batches = json.loads(proc.stdout)
    if not isinstance(batches, list) or not batches:
        raise RuntimeError("D1 returned no result")
    rows = []
    for batch in batches:
        if batch.get("success") is not True or not isinstance(batch.get("results"), list):
            raise RuntimeError("D1 did not confirm the query succeeded")
        rows.extend(batch["results"])
    return rows


def deidentified(
    sessions: list[dict[str, Any]], responses: list[dict[str, Any]]
) -> tuple[str, str]:
    """Keep the analysis columns, but no browser hash or original session identifiers."""
    texts = part2_export_texts(sessions, responses)
    part2_ids = {str(s["id"]): f"p2-{i + 1}" for i, s in enumerate(sessions)}
    session_ids = {str(s["session_id"]): f"s-{i + 1}" for i, s in enumerate(sessions)}
    clean = []
    for text in texts:
        reader = csv.DictReader(io.StringIO(text))
        fields = [f for f in reader.fieldnames or [] if f != "client_token_hash"]
        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in reader:
            row.pop("client_token_hash", None)
            row["part2_id"] = part2_ids[row["part2_id"]]
            if "session_id" in row:
                row["session_id"] = session_ids[row["session_id"]]
            writer.writerow(row)
        clean.append(out.getvalue())
    return clean[0], clean[1]


def save(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        path.chmod(0o600)
        file.write(text)
        file.flush()
        os.fsync(file.fileno())


def cleanup(now: datetime, query: Query = d1, archives: Path = ARCHIVES) -> str:
    if now < DELETE_AT:
        return "not due until 2026-11-30 at 09:00 Pacific; nothing read or deleted"
    receipt = archives / "completed.json"
    if receipt.exists():
        return "already completed; nothing read or deleted"
    sessions = query("SELECT * FROM part2_session ORDER BY offered_at")
    responses = query("SELECT * FROM part2_response ORDER BY part2_id, position")
    texts = deidentified(sessions, responses)
    archives.mkdir(parents=True, exist_ok=True, mode=0o700)
    archives.chmod(0o700)
    folder = Path(tempfile.mkdtemp(prefix="export-", dir=archives))
    for name, text in zip(("part2_sessions.csv", "part2_responses.csv"), texts, strict=True):
        save(folder / name, text)
    # No delete is sent until both exports have reached disk. No other table is targeted.
    query(DELETE_SQL)
    counts = query(
        "SELECT COUNT(*) AS n FROM part2_session UNION ALL SELECT COUNT(*) AS n FROM part2_response"
    )
    if len(counts) != 2 or any(row["n"] != 0 for row in counts):
        raise RuntimeError("part 2 rows remain; export kept, completion not recorded")
    record = {
        "completed_utc": now.isoformat(),
        "export": folder.name,
        "tables": ["part2_response", "part2_session"],
        "sessions_exported": len(sessions),
        "responses_exported": len(responses),
    }
    pending = archives / "completed.tmp"
    save(pending, json.dumps(record, indent=2) + "\n")
    pending.replace(receipt)
    return "de-identified export kept; part2_response and part2_session cleared; receipt saved"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(
            "part2-retention: plan only; on 2026-11-30 at 09:00 Pacific, export then " + DELETE_SQL
        )
        return 0
    try:
        print("part2-retention: " + cleanup(datetime.now(UTC)))
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        # Never print D1 rows or captured command output.
        print(f"part2-retention: failed ({type(error).__name__}); inspect the private job log")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
