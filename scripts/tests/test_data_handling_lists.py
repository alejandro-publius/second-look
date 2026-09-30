"""docs/DATA_HANDLING.md names every place the code stores something.

The consent screen and the privacy page point people to that file, and SECURITY.md calls it the
full list. On Sep 29 it had fallen behind the code: part 2's tables, the language of a check and
the language kept on the phone were stored and not named. So this reads the code and fails when
the file leaves out a table of the live database, a file of the export, or a key the web app
writes into the browser's storage.

It checks that each is named, not what is said about it. A person still has to read the words.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "DATA_HANDLING.md"
SCHEMA = ROOT / "worker" / "schema.sql"
WORKER_SRC = ROOT / "worker" / "src"
WEB = ROOT / "apps" / "web"
WEB_FOLDERS = ("lib", "components", "app")

TABLE = re.compile(r"^CREATE TABLE IF NOT EXISTS (\w+)", re.M)
COLUMN = re.compile(r"^ALTER TABLE (\w+) ADD COLUMN (\w+)", re.M)
CSV_NAME = re.compile(r'name: "([a-z0-9_]+\.csv)"')
WRITE = re.compile(
    r"\b(localStorage|sessionStorage)\s*\.\s*setItem\(\s*([A-Za-z_$][\w$]*|\"[^\"]+\"|'[^']+')"
)
OPEN_DB = re.compile(r"\bindexedDB\s*\.\s*open\(\s*([A-Za-z_$][\w$]*|\"[^\"]+\"|'[^']+')")


class Unreadable(Exception):
    """A storage key that is not a plain string, so this cannot say what it is."""


def named(doc: str) -> set[str]:
    """Everything the file puts in code marks."""
    return set(re.findall(r"`([^`\n]+)`", doc))


def tables(schema: str) -> list[str]:
    return TABLE.findall(schema)


def export_files(sources: list[str]) -> list[str]:
    return [name for text in sources for name in CSV_NAME.findall(text)]


def resolve(arg: str, source: str) -> str:
    if arg[0] in "\"'":
        return arg[1:-1]
    found = re.search(
        rf"\b(?:const|let|var)\s+{re.escape(arg)}\s*(?::[^=]+)?=\s*[\"']([^\"']+)[\"']", source
    )
    if found is None:
        raise Unreadable(arg)
    return found.group(1)


def storage_keys(source: str) -> list[tuple[str, str]]:
    """Each write to the browser's storage in one file: the kind of storage and the key."""
    out = [(kind, resolve(arg, source)) for kind, arg in WRITE.findall(source)]
    out += [("indexedDB", resolve(arg, source)) for arg in OPEN_DB.findall(source)]
    return out


def web_sources() -> list[Path]:
    files: list[Path] = []
    for folder in WEB_FOLDERS:
        for path in sorted((WEB / folder).rglob("*")):
            if path.suffix in {".ts", ".tsx"} and path.is_file():
                files.append(path)
    return files


def missing(doc: str, wanted: list[str]) -> list[str]:
    have = named(doc)
    return sorted({w for w in wanted if w not in have})


# How the readers read ---------------------------------------------------------------------------


def test_tables_and_export_files_are_read_from_the_code() -> None:
    schema = "CREATE TABLE IF NOT EXISTS visit (\n  id TEXT\n);\n-- CREATE TABLE IF NOT EXISTS no\n"
    assert tables(schema) == ["visit"]
    assert export_files(['{ name: "sessions.csv", text }', 'name: "part2_sessions.csv"']) == [
        "sessions.csv",
        "part2_sessions.csv",
    ]


def test_storage_keys_are_read_through_their_constants() -> None:
    source = (
        'const KEY = "sl_one";\nexport const OTHER: string = "sl.two";\nconst DB_NAME = "store";\n'
        'localStorage.setItem(KEY, v);\nsessionStorage.setItem("sl_three", v);\n'
        "localStorage.setItem(OTHER, v);\nconst req = indexedDB.open(DB_NAME, 2);\n"
        "localStorage.getItem(UNSEEN);\n"
    )
    assert storage_keys(source) == [
        ("localStorage", "sl_one"),
        ("sessionStorage", "sl_three"),
        ("localStorage", "sl.two"),
        ("indexedDB", "store"),
    ]


def test_a_key_that_is_not_a_plain_string_is_refused() -> None:
    try:
        storage_keys("localStorage.setItem(keyFor(user), v);\nconst keyFor = 1;\n")
    except Unreadable:
        return
    raise AssertionError("a computed key was read as if it were known")


def test_a_name_counts_only_inside_code_marks() -> None:
    doc = "- `part2_session`: one row.\nThe table part2_response is not marked.\n"
    assert missing(doc, ["part2_session", "part2_response"]) == ["part2_response"]


# The file itself --------------------------------------------------------------------------------


def test_every_table_of_the_live_database_is_named() -> None:
    found = tables(SCHEMA.read_text(encoding="utf-8"))
    assert len(found) >= 19, found
    assert missing(DOC.read_text(encoding="utf-8"), found) == []


def test_every_column_a_migration_adds_is_named() -> None:
    doc = DOC.read_text(encoding="utf-8")
    added = [
        hit
        for path in sorted((ROOT / "worker" / "migrations").glob("*.sql"))
        for hit in COLUMN.findall(path.read_text(encoding="utf-8"))
    ]
    assert added, "no migration adds a column, so this test reads nothing"
    for table, column in added:
        assert f"`{table}`" in doc, table
        assert re.search(rf"\b{re.escape(column)}\b", doc), f"{table}.{column}"


def test_every_file_of_the_export_is_named() -> None:
    sources = [p.read_text(encoding="utf-8") for p in sorted(WORKER_SRC.glob("*.ts"))]
    found = export_files(sources)
    assert len(found) >= 4, found
    assert missing(DOC.read_text(encoding="utf-8"), found) == []


def test_every_key_the_web_app_writes_on_the_phone_is_named() -> None:
    found: list[tuple[str, str]] = []
    for path in web_sources():
        found += storage_keys(path.read_text(encoding="utf-8"))
    kinds = {kind for kind, _ in found}
    assert kinds == {"localStorage", "sessionStorage", "indexedDB"}, kinds
    assert len({key for _, key in found}) >= 9, found
    assert missing(DOC.read_text(encoding="utf-8"), [key for _, key in found]) == []
