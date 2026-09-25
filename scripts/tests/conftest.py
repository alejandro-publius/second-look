"""Shared test setup for scripts/tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import deploy_record


@pytest.fixture(autouse=True)
def _no_test_touches_the_real_deploy_archives(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A test that recorded a Worker deploy once pruned ~/second-look-backups/deploys/ and deleted
    the site build kept for rollback. Every test gets its own archive folder instead."""
    monkeypatch.setattr(deploy_record, "ARCHIVES", Path(tmp_path_factory.mktemp("deploys")))
