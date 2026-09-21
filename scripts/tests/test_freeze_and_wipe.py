"""freeze_key refuses placeholders and logs; wipe needs the phrase and touches study tables only."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
import yaml
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, func, select

from scripts import audit_log, freeze_key, wipe_for_launch
from scripts.ingest_photos import MANIFEST_COLUMNS

REPO = Path(__file__).parents[2]


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    """The real content/test_items.yaml and manifest, copied so tests can edit them."""
    r = tmp_path / "repo"
    (r / "content").mkdir(parents=True)
    (r / "photos").mkdir()
    (r / "docs").mkdir()
    shutil.copy(REPO / "content" / "test_items.yaml", r / "content")
    shutil.copy(REPO / "photos" / "manifest.csv", r / "photos")
    return r


def set_manifest(root: Path, **changes: str) -> None:
    path = root / "photos" / "manifest.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row["role"] == "test":
            row.update(changes)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def test_key_hash_is_order_free_and_changes_with_gold() -> None:
    a = [{"id": "t02", "gold": "absent"}, {"id": "t01", "gold": "present"}]
    b = [{"id": "t01", "gold": "present"}, {"id": "t02", "gold": "absent"}]
    c = [{"id": "t01", "gold": "absent"}, {"id": "t02", "gold": "absent"}]
    assert freeze_key.key_hash(a) == freeze_key.key_hash(b)
    assert freeze_key.key_hash(a) != freeze_key.key_hash(c)
    assert len(freeze_key.key_hash(a)) == 64


def test_freeze_refuses_placeholders_and_writes_nothing(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert freeze_key.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "refused, nothing written" in out
    assert "is a placeholder" in out and "has no second label" in out
    assert not (root / "results" / "key_hash.json").exists()
    assert not (root / "audit" / "log.jsonl").exists()


def test_freeze_with_allow_placeholders_marks_synthetic(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert freeze_key.main(["--root", str(root), "--allow-placeholders"]) == 0
    out = capsys.readouterr().out
    assert "placeholders true" in out and "SYNTHETIC" in out
    record = json.loads((root / "results" / "key_hash.json").read_text())
    assert record["placeholders"] is True and record["synthetic"] is True
    assert record["stamp"] == "SYNTHETIC"
    assert record["n_items"] == 16
    assert record["key_sha256"] == freeze_key.key_hash(freeze_key.load_items(root))
    log = root / "audit" / "log.jsonl"
    assert audit_log.verify(log) == 1
    entry = json.loads(log.read_text().splitlines()[0])
    assert entry["kind"] == "key_frozen" and entry["hash"] == record["audit_hash"]


def test_freeze_passes_with_real_licenses_and_second_labels(root: Path) -> None:
    set_manifest(root, license="own-CC-BY-4.0", labeller_2="present")
    record = freeze_key.freeze(root)
    assert record["placeholders"] is False and record["synthetic"] is False
    assert "stamp" not in record
    assert audit_log.verify(root / "audit" / "log.jsonl") == 1


def test_freeze_refuses_when_items_and_manifest_disagree(root: Path) -> None:
    set_manifest(root, license="own-CC-BY-4.0", labeller_2="present", gold_label="absent")
    with pytest.raises(freeze_key.FreezeError, match="disagrees"):
        freeze_key.freeze(root, allow_placeholders=True)


def test_freeze_hash_changes_when_an_item_flips(root: Path) -> None:
    set_manifest(root, license="own-CC-BY-4.0", labeller_2="present")
    before = freeze_key.freeze(root)["key_sha256"]
    items_path = root / "content" / "test_items.yaml"
    doc = yaml.safe_load(items_path.read_text())
    doc["items"][0]["gold"] = "absent"
    items_path.write_text(yaml.safe_dump(doc))
    set_manifest(root, license="own-CC-BY-4.0", labeller_2="absent", gold_label="absent")
    # every test photo is now absent, which the loader would refuse, but the hash must still move
    with pytest.raises(freeze_key.FreezeError):
        freeze_key.freeze(root)  # items 2..16 now disagree with the manifest
    doc = yaml.safe_load(items_path.read_text())
    for item in doc["items"]:
        item["gold"] = "absent"
    items_path.write_text(yaml.safe_dump(doc))
    after = freeze_key.freeze(root)["key_sha256"]
    assert before != after
    assert audit_log.verify(root / "audit" / "log.jsonl") == 2


def study_db(tmp_path: Path) -> tuple[object, MetaData]:
    metadata = MetaData()
    session = Table(
        "session", metadata, Column("id", String, primary_key=True), Column("arm", String)
    )
    response = Table(
        "response",
        metadata,
        Column("session_id", String, primary_key=True),
        Column("item_id", String, primary_key=True),
    )
    observer = Table("observer", metadata, Column("contributor_token", String, primary_key=True))
    spot = Table("spot", metadata, Column("id", Integer, primary_key=True), Column("name", String))
    engine = create_engine(f"sqlite:///{tmp_path / 'study.db'}")
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            session.insert(), [{"id": "s1", "arm": "trained"}, {"id": "s2", "arm": "untrained"}]
        )
        conn.execute(
            response.insert(),
            [
                {"session_id": "s1", "item_id": "t01"},
                {"session_id": "s1", "item_id": "t02"},
                {"session_id": "s2", "item_id": "t01"},
            ],
        )
        conn.execute(observer.insert(), [{"contributor_token": "abcdefgh12345678"}])
        conn.execute(spot.insert(), [{"id": 1, "name": "Strawberry Creek at Oxford"}])
    return engine, metadata


def counts(engine: object, metadata: MetaData) -> dict[str, int]:
    out = {}
    with engine.connect() as conn:  # type: ignore[attr-defined]
        for name, table in metadata.tables.items():
            out[name] = int(conn.execute(select(func.count()).select_from(table)).scalar_one())
    return out


def test_wipe_deletes_only_study_tables_after_the_phrase(tmp_path: Path) -> None:
    engine, metadata = study_db(tmp_path)
    assert counts(engine, metadata) == {"session": 2, "response": 3, "observer": 1, "spot": 1}
    deleted = wipe_for_launch.wipe(engine, metadata, "wipe the study tables")  # type: ignore[arg-type]
    assert deleted == {"response": 3, "observer": 1, "session": 2}
    assert counts(engine, metadata) == {"session": 0, "response": 0, "observer": 0, "spot": 1}


def test_wipe_refuses_wrong_phrase_and_missing_tables(tmp_path: Path) -> None:
    engine, metadata = study_db(tmp_path)
    with pytest.raises(wipe_for_launch.WipeError, match="did not match"):
        wipe_for_launch.wipe(engine, metadata, "yes")  # type: ignore[arg-type]
    with pytest.raises(wipe_for_launch.WipeError, match="did not match"):
        wipe_for_launch.wipe(engine, metadata, "")  # type: ignore[arg-type]
    assert counts(engine, metadata)["session"] == 2
    partial = MetaData()
    Table("session", partial, Column("id", String, primary_key=True))
    with pytest.raises(wipe_for_launch.WipeError, match="not defined in apps.api.models yet"):
        wipe_for_launch.wipe(engine, partial, "wipe the study tables")  # type: ignore[arg-type]


def test_wipe_record_writes_deviation_line_and_audit_entry(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "deviations.md").write_text("# Deviations\n\nNone yet.", encoding="utf-8")
    digest = wipe_for_launch.record(root, {"response": 3, "observer": 1, "session": 2})
    text = (root / "docs" / "deviations.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "# Deviations" and lines[2] == "None yet."
    assert lines[3].startswith("- 20") and "launch wipe" in lines[3]
    assert "Deleted 2 session, 3 response and 1 observer rows" in lines[3]
    log = root / "audit" / "log.jsonl"
    assert audit_log.verify(log) == 1
    entry = json.loads(log.read_text().splitlines()[0])
    assert entry["kind"] == "launch_wipe" and entry["hash"] == digest


def test_wipe_cli_refuses_while_w1_tables_are_missing_or_phrase_wrong(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Against the real apps.api.models: either the tables are not there yet, or the wrong
    phrase stops it. Either way nothing is deleted and the exit code is 1."""
    code = wipe_for_launch.main(["--confirm", "no thanks", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 1 and "refused" in out
    assert not (tmp_path / "docs" / "deviations.md").exists()
