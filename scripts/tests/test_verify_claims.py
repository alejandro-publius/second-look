"""verify_claims: a claim marker and a rendered number both have to match results/."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import verify_claims as vc


def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, readme: str, doc: dict) -> int:
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "x.json").write_text(json.dumps(doc))
    (tmp_path / "README.md").write_text(readme)
    monkeypatch.setattr(vc, "ROOT", tmp_path)
    monkeypatch.setattr(vc, "README", tmp_path / "README.md")
    monkeypatch.setattr("sys.argv", ["verify_claims.py"])
    return vc.main()


def test_a_rendered_number_that_matches_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme = "Frames: <!--v:results/x.json#/frames-->42<!--/v-->."
    assert run(tmp_path, monkeypatch, readme, {"frames": 42}) == 0


def test_a_rendered_number_that_drifted_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme = "Frames: <!--v:results/x.json#/frames-->42<!--/v-->."
    assert run(tmp_path, monkeypatch, readme, {"frames": 43}) == 1


def test_a_rendered_synthetic_number_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    readme = "Frames: <!--v:results/x.json#/frames-->42<!--/v-->."
    assert run(tmp_path, monkeypatch, readme, {"frames": 42, "synthetic": True}) == 1


def test_a_token_nobody_rendered_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert run(tmp_path, monkeypatch, "{{claim:results/x.json#/frames}}", {"frames": 1}) == 1


def test_another_file_is_checked_the_same_way(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "x.json").write_text(json.dumps({"frames": 46}))
    (tmp_path / "README.md").write_text("nothing here")
    (tmp_path / "devpost.md").write_text("<!-- claim: results/x.json#/frames = 45 -->")
    monkeypatch.setattr(vc, "ROOT", tmp_path)
    monkeypatch.setattr(vc, "README", tmp_path / "README.md")
    monkeypatch.setattr("sys.argv", ["verify_claims.py", "--file", "devpost.md"])
    assert vc.main() == 1


def test_a_named_simulation_is_checked_and_may_be_cited_without_synthetic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(vc, "SIMULATIONS", frozenset({"results/x.json"}))
    readme = "Groups: <!--v:results/x.json#/n-->5<!--/v-->. <!-- claim: results/x.json#/n = 5 -->"
    assert run(tmp_path, monkeypatch, readme, {"n": 5, "synthetic": True}) == 0


def test_a_named_simulation_that_drifted_still_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(vc, "SIMULATIONS", frozenset({"results/x.json"}))
    readme = "Groups: <!--v:results/x.json#/n-->5<!--/v-->."
    assert run(tmp_path, monkeypatch, readme, {"n": 7, "synthetic": True}) == 1


def test_only_the_coarseness_simulation_is_named() -> None:
    assert vc.SIMULATIONS == frozenset({"results/consensus_coarseness.json"})


def test_a_pointer_with_a_space_is_checked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Pair keys such as "model a vs model b" hold spaces.
    readme = "Agree: <!--v:results/x.json#/pairs/a vs b/agree-->41<!--/v-->."
    assert run(tmp_path, monkeypatch, readme, {"pairs": {"a vs b": {"agree": 41}}}) == 0
    assert run2(tmp_path, monkeypatch, readme, {"pairs": {"a vs b": {"agree": 40}}}) == 1


def run2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, readme: str, doc: dict) -> int:
    (tmp_path / "results" / "x.json").write_text(json.dumps(doc))
    (tmp_path / "README.md").write_text(readme)
    monkeypatch.setattr("sys.argv", ["verify_claims.py"])
    return vc.main()
