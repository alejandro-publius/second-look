"""Wipe the study tables before the first real participant, and say so in two places.

Run: uv run python scripts/wipe_for_launch.py
It asks you to type the phrase "wipe the study tables", deletes every row from the session,
response and observer tables through the API's own database module, appends a dated line to
docs/deviations.md and a launch_wipe entry to the audit log (master brief section 6 item 10).
Nothing else is touched: spots, visits, uploads and the sandbox cache stay.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.engine import Engine

from scripts import audit_log

ROOT = Path(__file__).resolve().parents[1]
PHRASE = "wipe the study tables"
STUDY_TABLES = ("response", "observer", "session")  # children first, for foreign keys


class WipeError(Exception):
    """Refused. No row was deleted."""


def find_tables(metadata: MetaData) -> dict[str, Table]:
    missing = [t for t in STUDY_TABLES if t not in metadata.tables]
    if missing:
        raise WipeError(
            f"study tables not defined in apps.api.models yet: {missing}; nothing wiped"
        )
    return {t: metadata.tables[t] for t in STUDY_TABLES}


def wipe(engine: Engine, metadata: MetaData, confirm: str) -> dict[str, int]:
    """Delete every row from the study tables. Returns rows deleted per table."""
    if confirm.strip() != PHRASE:
        raise WipeError(f"confirmation phrase did not match {PHRASE!r}; nothing wiped")
    tables = find_tables(metadata)
    counts: dict[str, int] = {}
    with engine.begin() as conn:
        for name in STUDY_TABLES:
            table = metadata.tables[name]
            counts[name] = int(conn.execute(select(func.count()).select_from(table)).scalar_one())
        for name in STUDY_TABLES:
            conn.execute(tables[name].delete())
    return counts


def record(root: Path, counts: dict[str, int]) -> str:
    """Append the deviation line and the audit entry. Returns the audit hash."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
        f"- {now}: launch wipe. Deleted {counts['session']} session, {counts['response']} response "
        f"and {counts['observer']} observer rows (dry runs and QA) before the first real "
        "participant, as the plan's exclusions say. Logged as launch_wipe in audit/log.jsonl.\n"
    )
    deviations = root / "docs" / "deviations.md"
    text = deviations.read_text(encoding="utf-8") if deviations.exists() else ""
    if not text.endswith("\n") and text:
        text += "\n"
    deviations.write_text(text + line, encoding="utf-8")
    return audit_log.append(
        "launch_wipe", {"ts_utc": now, **counts}, path=root / "audit" / "log.jsonl"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--confirm", default=None, help=f"the phrase {PHRASE!r}, else prompted")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    from sqlmodel import SQLModel

    from apps.api import models  # noqa: F401  registers the tables on SQLModel.metadata
    from apps.api.db import engine

    try:
        find_tables(SQLModel.metadata)
    except WipeError as e:
        print(f"wipe: refused: {e}")
        return 1
    url = engine.url.render_as_string(hide_password=True)
    print(f"wipe: database {url}")
    print("wipe: this deletes every session, response and observer row. It cannot be undone.")
    phrase = args.confirm if args.confirm is not None else input(f"Type '{PHRASE}' to go on: ")
    try:
        counts = wipe(engine, SQLModel.metadata, phrase)
    except WipeError as e:
        print(f"wipe: refused: {e}")
        return 1
    digest = record(args.root.resolve(), counts)
    summary = ", ".join(f"{k} {v}" for k, v in counts.items())
    print(f"wipe: deleted rows: {summary}; noted in docs/deviations.md; audit hash {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
