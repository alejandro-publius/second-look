"""Shared fixtures: one seeded synthetic data set per scenario, generated once per test run."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from evals.make_synthetic_sessions import SCENARIOS, write_scenario
from evals.usability_analysis import load_export

Loader = Callable[[str], tuple[pd.DataFrame, pd.DataFrame]]


@pytest.fixture(scope="session")
def synthetic_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("synthetic")
    for scenario in SCENARIOS:
        write_scenario(scenario, root)
    return root


@pytest.fixture(scope="session")
def loaded(synthetic_root: Path) -> Loader:
    cache: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}

    def _load(scenario: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        if scenario not in cache:
            cache[scenario] = load_export(synthetic_root / scenario)
        return cache[scenario]

    return _load
