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


def test_a_block_is_checked_whole_against_its_results_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Critic round 14 A04: the README's recorded judge-check run is a block made from
    # results/judge_check.json, so a block that no longer matches the file is a drifted claim.
    from scripts.render_readme import judge_check_list

    run_doc = {"steps": [{"name": "tests", "ok": True, "text": "python: 3 passed"}], "last": "ok"}
    body = judge_check_list(run_doc)
    readme = f"Run:\n\n<!--block:judge-check results/x.json-->\n{body}<!--/block-->\n"
    assert run(tmp_path, monkeypatch, readme, run_doc) == 0
    drifted = {**run_doc, "last": "judge-check: 1 of 1 steps failed"}
    (tmp_path / "results" / "x.json").write_text(json.dumps(drifted))
    assert vc.main() == 1
    assert "rendered block drifted: judge-check from results/x.json" in capsys.readouterr().out
    (tmp_path / "results" / "x.json").write_text(json.dumps({"no": "steps"}))
    assert vc.main() == 1


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


CITY_IMG = '<img src="docs/screens/city.webp" width="200" alt="{alt}">'


def run_with_screens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, readme: str, alt: str) -> int:
    (tmp_path / "results").mkdir()
    row = {"file": "docs/screens/city.webp", "alt": alt}
    (tmp_path / "results" / "screens.json").write_text(json.dumps({"images": [row]}))
    (tmp_path / "README.md").write_text(readme)
    monkeypatch.setattr(vc, "ROOT", tmp_path)
    monkeypatch.setattr(vc, "README", tmp_path / "README.md")
    monkeypatch.setattr("sys.argv", ["verify_claims.py"])
    return vc.main()


def test_an_image_alt_that_matches_the_gallery_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alt = "The city view before anyone has checked it: no visits yet."
    assert run_with_screens(tmp_path, monkeypatch, CITY_IMG.format(alt=alt), alt) == 0


def test_an_image_alt_that_differs_from_the_gallery_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # REVIEW_03 R27: the README said the city screenshot showed measures; it shows none.
    readme = CITY_IMG.format(alt="The city view: what volunteers found and what to do.")
    alt = "The city view before anyone has checked it: no visits yet."
    assert run_with_screens(tmp_path, monkeypatch, readme, alt) == 1
    assert "alt text drifted: docs/screens/city.webp" in capsys.readouterr().out


def test_an_image_with_a_gallery_row_and_no_alt_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme = '<img src="docs/screens/city.webp" width="200">'
    assert run_with_screens(tmp_path, monkeypatch, readme, "The city view.") == 1


def test_an_escaped_alt_is_compared_as_it_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme = CITY_IMG.format(alt="Rain &amp; &quot;dry&quot; days.")
    assert run_with_screens(tmp_path, monkeypatch, readme, 'Rain & "dry" days.') == 0


def test_every_readme_image_alt_matches_the_gallery() -> None:
    # The committed files: every README image with a gallery row, the GIF and lesson photos too.
    compared, problems = vc.alt_problems(vc.README.read_text(encoding="utf-8"))
    page = vc.ROOT / vc.GALLERY_PAGE
    more, drifted = vc.alt_problems(page.read_text(encoding="utf-8"), "docs/screens/")
    assert problems == [] and drifted == []
    assert compared >= 5 and more >= 30
