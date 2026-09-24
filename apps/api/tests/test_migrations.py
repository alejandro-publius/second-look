"""The Alembic migration builds the same schema as the models, on a fresh SQLite file."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

import apps.api.models  # noqa: F401

ROOT = Path(__file__).resolve().parents[3]
STRUCTURAL = {
    "add_table",
    "remove_table",
    "add_column",
    "remove_column",
    "add_index",
    "remove_index",
}


def _config(url: str) -> Config:
    cfg = Config(str(ROOT / "apps" / "api" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "apps" / "api" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_head_matches_the_models_and_downgrade_removes_everything(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/migrated.db"
    monkeypatch.setitem(os.environ, "DATABASE_URL", url)
    command.upgrade(_config(url), "head")
    engine = create_engine(url)
    names = set(inspect(engine).get_table_names())
    expected = {
        "session",
        "response",
        "observer",
        "spot",
        "visit",
        "check_result",
        "upload",
        "sandbox_cache",
        "inaturalist_cache",
        "randomization_counter",
        "skeleton_ping",
    }
    assert expected <= names, expected - names
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        diffs = compare_metadata(ctx, SQLModel.metadata)
    structural = [d for d in diffs if (d[0] if isinstance(d, tuple) else d[0][0]) in STRUCTURAL]
    assert structural == [], structural
    command.downgrade(_config(url), "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
