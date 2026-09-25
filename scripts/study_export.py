"""The study tables from a D1 backup, as the two CSV files the live export route gives.

The lock job (scripts/lock_analysis.py) takes a backup of the study database with
scripts/backup_d1.sh and exports the study tables from that file, so the one pre-registered run
reads exactly the snapshot that is kept, and no export token is needed. The files are the ones
`/api/test/export` returns: `exportZip` in worker/src/index.ts, row for row and byte for byte, which
scripts/tests/test_study_export.py checks by running the Worker's own code on the same rows.

  uv run python scripts/study_export.py ~/second-look-backups/second-look-<stamp>.sql data/export
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "worker" / "src" / "content.json"

SESSION_HEAD = [
    "session_id", "arm", "block_id", "source_label", "ua_class", "consent_version",
    "content_hash", "build_hash", "started_at_utc", "lesson_seconds_total", "completed_at_utc",
    "test_seconds", "is_test", "post_lock", "hidden_field_filled", "client_token_hash",
    "prior_experience", "warmup_choice", "unsent_count",
]  # fmt: skip
RESPONSE_HEAD = [
    "session_id", "item_id", "feature", "gold", "answer", "correct", "rt_ms", "position",
    "first_choice", "final_choice", "t_first_ms", "t_confirm_ms", "n_changes",
]  # fmt: skip
SESSIONS_SQL = "SELECT * FROM session ORDER BY started_at"
RESPONSES_SQL = "SELECT * FROM response ORDER BY session_id, position"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def load_dump(sql_path: Path) -> sqlite3.Connection:
    """A throwaway SQLite database made from a `wrangler d1 export` file."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(sql_path.read_text(encoding="utf-8"))
    return conn


def rows(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The two SELECTs the Worker's export runs, in its order."""
    sessions = [dict(r) for r in conn.execute(SESSIONS_SQL)]
    responses = [dict(r) for r in conn.execute(RESPONSES_SQL)]
    return sessions, responses


def js_number(x: float) -> str:
    """A number as JavaScript's String() writes it (ECMAScript Number::toString)."""
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    parts = Decimal(repr(abs(x))).normalize().as_tuple()
    digits = "".join(str(d) for d in parts.digits)
    k = len(digits)
    n = int(parts.exponent) + k
    if k <= n <= 21:
        text = digits + "0" * (n - k)
    elif 0 < n <= 21:
        text = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        text = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        mantissa = digits[0] + ("." + digits[1:] if k > 1 else "")
        text = f"{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"
    return sign + text


def js_string(v: Any) -> str:
    """String(v) in the Worker for what D1 hands back: text, integers, reals or null."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return js_number(v)
    return str(v)


def js_round(x: float) -> float:
    """Math.round: halves go up, toward positive infinity."""
    if math.isnan(x) or math.isinf(x):
        return x
    return float(math.floor(x + 0.5))


def js_date_ms(text: str) -> float:
    """Date.parse for the ISO times the Worker stores; NaN when it cannot read one."""
    try:
        ts = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return math.nan
    if ts.tzinfo is None:
        return math.nan
    # Whole milliseconds, as Date.parse keeps them.
    return float((ts - EPOCH) // timedelta(milliseconds=1))


def js_object_values(obj: dict[str, Any]) -> list[Any]:
    """Object.values in JavaScript's key order: array index keys first, in number order."""

    def is_index(k: str) -> bool:
        return re.fullmatch(r"0|[1-9]\d*", k) is not None and int(k) < 2**32 - 1

    index_keys = sorted((k for k in obj if is_index(k)), key=int)
    return [obj[k] for k in index_keys] + [v for k, v in obj.items() if not is_index(k)]


def nullish(v: Any) -> Any:
    """v ?? "" in JavaScript: only null and undefined become the empty string."""
    return "" if v is None else v


def csv_cell(v: Any) -> str:
    s = js_string(v)
    return '"' + s.replace('"', '""') + '"' if re.search(r'[",\n]', s) else s


def csv_row(cells: list[Any]) -> str:
    return ",".join(csv_cell(c) for c in cells)


def items() -> tuple[dict[str, str], dict[str, str]]:
    content = json.loads(CONTENT.read_text(encoding="utf-8"))
    gold = {str(i["id"]): str(i["gold"]) for i in content["test_items"]}
    feature = {str(i["id"]): str(i["feature"]) for i in content["test_items"]}
    return gold, feature


def is_correct(answer: str, gold: str) -> bool:
    return (answer == "yes" and gold == "present") or (answer == "no" and gold == "absent")


def export_texts(
    sessions: list[dict[str, Any]], responses: list[dict[str, Any]]
) -> tuple[str, str]:
    """sessions.csv and responses.csv, as exportZip in worker/src/index.ts writes them."""
    gold_of, feature_of = items()
    first_at: dict[str, str] = {}
    for r in responses:
        sid, at = js_string(r["session_id"]), js_string(r["received_at"])
        if sid not in first_at or at < first_at[sid]:
            first_at[sid] = at
    session_lines = [csv_row(list(SESSION_HEAD))]
    for s in sessions:
        lesson_total: Any = ""
        if s.get("lesson_seconds"):
            parsed = json.loads(str(s["lesson_seconds"]))
            values = (
                js_object_values(parsed)
                if isinstance(parsed, dict)
                else (parsed if isinstance(parsed, list) else [])
            )
            total = 0.0
            for v in values:
                total += 0.0 if v is None else float(v)  # JavaScript: 0 + null is 0
            lesson_total = js_round(total * 10) / 10
        test_seconds: Any = ""
        first = first_at.get(js_string(s["id"]))
        if s.get("completed_at") and first:
            ms = js_date_ms(js_string(s["completed_at"])) - js_date_ms(first)
            test_seconds = js_round((ms / 1000) * 10) / 10
        session_lines.append(
            csv_row(
                [
                    s["id"],
                    s["arm"],
                    s["block_id"],
                    s["source_label"],
                    s["ua_class"],
                    s["consent_version"],
                    s["content_hash"],
                    s["build_hash"],
                    s["started_at"],
                    lesson_total,
                    nullish(s.get("completed_at")),
                    test_seconds,
                    s["is_test"],
                    s["post_lock"],
                    s["hidden_field_filled"],
                    s["client_token_hash"],
                    nullish(s.get("prior_experience")),
                    nullish(s.get("warmup_choice")),
                    s["unsent_count"],
                ]
            )  # fmt: skip
        )
    response_lines = [csv_row(list(RESPONSE_HEAD))]
    for r in responses:
        item_id = js_string(r["item_id"])
        gold = gold_of.get(item_id)
        right = 1 if gold and is_correct(js_string(r["answer"]), gold) else 0
        response_lines.append(
            csv_row(
                [
                    r["session_id"],
                    item_id,
                    feature_of.get(item_id, ""),
                    gold or "",
                    r["answer"],
                    right,
                    r["rt_ms"],
                    r["position"],
                    nullish(r.get("first_choice")),
                    r["answer"],
                    nullish(r.get("t_first_ms")),
                    r["rt_ms"],
                    r["n_changes"],
                ]
            )  # fmt: skip
        )
    return "\r\n".join(session_lines) + "\r\n", "\r\n".join(response_lines) + "\r\n"


def export(sql_path: Path, out_dir: Path) -> dict[str, Any]:
    """Write sessions.csv and responses.csv from a backup file; say how many rows each holds."""
    conn = load_dump(sql_path)
    try:
        sessions, responses = rows(conn)
    finally:
        conn.close()
    session_text, response_text = export_texts(sessions, responses)
    out_dir.mkdir(parents=True, exist_ok=True)
    # newline="" keeps the \r\n the Worker writes, byte for byte.
    with (out_dir / "sessions.csv").open("w", encoding="utf-8", newline="") as f:
        f.write(session_text)
    with (out_dir / "responses.csv").open("w", encoding="utf-8", newline="") as f:
        f.write(response_text)
    return {"sessions": len(sessions), "responses": len(responses)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("backup", type=Path, help="a wrangler d1 export file")
    parser.add_argument("out_dir", type=Path, help="where sessions.csv and responses.csv go")
    args = parser.parse_args(argv)
    counts = export(args.backup, args.out_dir)
    print(
        f"study-export: {counts['sessions']} session rows and {counts['responses']} response rows "
        f"from {args.backup.name} into {args.out_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
