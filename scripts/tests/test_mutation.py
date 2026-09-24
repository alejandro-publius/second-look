"""make mutation reads mutmut's results honestly and refuses a run that proves nothing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import mutation

ROOT = mutation.ROOT


def meta(killed: int, survived: int, timeout: int = 0, unchecked: int = 0) -> dict[str, Any]:
    codes: dict[str, int | None] = {}
    for i in range(killed):
        codes[f"m.k_{i}"] = 1
    for i in range(survived):
        codes[f"m.s_{i}"] = 0
    for i in range(timeout):
        codes[f"m.t_{i}"] = 36
    for i in range(unchecked):
        codes[f"m.n_{i}"] = None
    return {"exit_code_by_key": codes}


def fake_run(tmp_path: Path, metas: dict[str, dict[str, Any]]) -> Path:
    for module, doc in metas.items():
        path = tmp_path / "mutants" / f"{module}.meta"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")
    return tmp_path


def counts(killed: int, survived: int, **kw: int) -> dict[str, Any]:
    return mutation.module_counts(meta(killed, survived, **kw), mutation.status_by_exit_code())


def test_counts_follow_mutmuts_own_reading_of_each_exit_code() -> None:
    c = counts(17, 2, timeout=1)
    assert (c["mutants"], c["killed"], c["survived"], c["timeout"]) == (20, 17, 2, 1)
    assert c["score_percent"] == 85.0
    assert c["survivors"] == ["m.s_0", "m.s_1"]


def test_a_timeout_is_not_counted_as_caught() -> None:
    assert counts(8, 0, timeout=2)["score_percent"] == 80.0


def test_every_module_at_the_line_passes() -> None:
    modules = {m: counts(85, 15) for m in mutation.MODULES}
    assert mutation.problems_with(modules) == []


def test_a_module_under_the_line_fails() -> None:
    modules = {m: counts(90, 10) for m in mutation.MODULES}
    modules["core/gate.py"] = counts(84, 16)
    assert mutation.problems_with(modules) == [
        "core/gate.py: 84.0 percent of changes caught, under 85"
    ]


def test_a_module_with_no_kill_fails_even_with_nothing_surviving() -> None:
    """No kill at all means the tests never ran the changed code: the harness proved nothing."""
    modules = {m: counts(90, 10) for m in mutation.MODULES}
    modules["core/scoring.py"] = {**counts(0, 0), "score_percent": 100.0}
    assert "core/scoring.py: no change was caught, so the tests never ran it" in (
        mutation.problems_with(modules)
    )


def test_a_change_never_checked_fails() -> None:
    modules = {m: counts(90, 10) for m in mutation.MODULES}
    modules["core/followups.py"] = counts(95, 0, unchecked=1)
    assert mutation.problems_with(modules) == ["core/followups.py: 1 changes never checked"]


def test_a_module_with_no_result_fails() -> None:
    modules = {m: counts(90, 10) for m in mutation.MODULES if m != "core/fhir_emit.py"}
    assert mutation.problems_with(modules) == ["core/fhir_emit.py: mutmut left no result"]


def test_a_good_run_writes_the_results_file(tmp_path: Path) -> None:
    root = fake_run(tmp_path, {m: meta(90, 10) for m in mutation.MODULES})
    out = tmp_path / "mutation.json"
    assert mutation.main(["--no-run", "--root", str(root), "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["tool"] == "mutmut" and doc["tool_version"]
    for module in mutation.MODULES:
        cell = doc["modules"][module]
        assert (cell["killed"], cell["survived"], cell["timeout"]) == (90, 10, 0)
        assert cell["score_percent"] == 90.0
    assert doc["total"]["mutants"] == 400
    assert doc["by_name"]["gate"] == {
        "mutants": 100,
        "killed": 90,
        "survived": 10,
        "timeout": 0,
        "score_percent": 90.0,
    }
    assert set(doc["by_name"]) == {"gate", "followups", "scoring", "fhir_emit"}


def test_a_run_under_the_line_writes_nothing(tmp_path: Path) -> None:
    metas = {m: meta(90, 10) for m in mutation.MODULES}
    metas["core/gate.py"] = meta(10, 90)
    root = fake_run(tmp_path, metas)
    out = tmp_path / "mutation.json"
    assert mutation.main(["--no-run", "--root", str(root), "--out", str(out)]) == 1
    assert not out.exists()


def test_the_committed_results_are_a_real_run_over_the_line() -> None:
    doc = json.loads((ROOT / "results" / "mutation.json").read_text(encoding="utf-8"))
    assert doc["tool"] == "mutmut" and doc["synthetic"] is False
    for module in mutation.MODULES:
        cell = doc["modules"][module]
        assert cell["killed"] > 0
        assert cell["mutants"] == cell["killed"] + cell["survived"] + cell["timeout"]
        assert cell["score_percent"] == round(100 * cell["killed"] / cell["mutants"], 1)
        assert cell["score_percent"] >= mutation.THRESHOLD_PERCENT
        assert len(cell["survivors"]) == cell["survived"]
        short = doc["by_name"][Path(module).stem]
        assert short == {k: cell[k] for k in mutation.SHORT_KEYS}


@pytest.mark.parametrize("module", mutation.MODULES)
def test_mutmut_is_told_to_change_exactly_these_modules(module: str) -> None:
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["mutmut"]
    assert module in config["only_mutate"]
    assert len(config["only_mutate"]) == len(mutation.MODULES)


def test_a_run_starts_from_an_empty_folder_with_no_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A result left from an earlier run must never be read as this run's."""
    fake_run(tmp_path, {"core/gate.py": meta(1, 0)})
    seen: dict[str, Any] = {}

    def run(argv: list[str], **kw: Any) -> Any:
        seen["stale_left"] = (tmp_path / "mutants").exists()
        seen["argv"] = argv
        seen["key"] = kw["env"].get("ANTHROPIC_API_KEY")
        return type("Done", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.setattr(mutation.subprocess, "run", run)
    assert mutation.run_mutmut(tmp_path) == 0
    assert seen["stale_left"] is False
    assert seen["argv"][1:4] == ["-m", "mutmut", "run"]
    assert seen["key"] is None
