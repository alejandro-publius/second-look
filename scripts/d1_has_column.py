"""Does a D1 table have a column? Reads wrangler's JSON answer on stdin.

scripts/deploy.sh asks the live database for a table's columns before it adds one, because
CREATE TABLE IF NOT EXISTS cannot add a column to a table that is already there (UPDATE_32):

  npx wrangler d1 execute second-look --remote --json \
    --command "SELECT name FROM pragma_table_info('visit')" \
    | uv run python scripts/d1_has_column.py language

Exit 0 when the column is there, 1 when the answer was read and the column is not in it, and 2
when the answer could not be read. The three are kept apart on purpose: an answer nobody could
read must never count as "missing", or the deploy would try to add a column that exists and fail.
Anything wrangler prints before the JSON, such as a notice of a new version, is skipped.
"""

from __future__ import annotations

import json
import sys

PRESENT, MISSING, UNREADABLE = 0, 1, 2


def columns(text: str) -> list[str] | None:
    """The column names in wrangler's answer, or None when it holds no readable answer."""
    start = text.find("[")
    if start < 0:
        return None
    try:
        doc = json.JSONDecoder().raw_decode(text[start:])[0]
    except ValueError:
        return None
    if not isinstance(doc, list) or not doc:
        return None
    names: list[str] = []
    for block in doc:
        if not isinstance(block, dict) or block.get("success") is False:
            return None
        rows = block.get("results")
        if not isinstance(rows, list):
            return None
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                return None
            names.append(row["name"])
    # A table with no column at all does not exist: that is not an answer about this column.
    return names or None


def state(text: str, column: str) -> int:
    names = columns(text)
    if names is None:
        return UNREADABLE
    return PRESENT if column in names else MISSING


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not args[0]:
        print("usage: d1_has_column.py COLUMN, with wrangler's JSON on stdin", file=sys.stderr)
        return UNREADABLE
    got = state(sys.stdin.read(), args[0])
    words = {PRESENT: "is there", MISSING: "is missing", UNREADABLE: "could not be read"}
    print(f"d1-has-column: {args[0]} {words[got]}", file=sys.stderr)
    return got


if __name__ == "__main__":
    raise SystemExit(main())
