"""The golden vectors are current, deterministic and cover every port the Worker carries."""

from __future__ import annotations

import json
from pathlib import Path

from evals import golden_vectors as gv

ROOT = Path(__file__).resolve().parents[2]


def test_committed_vectors_are_what_the_code_writes_today() -> None:
    """CI fails when Python changes and nobody re-ran the writer, so the TypeScript is always
    measured against the current reference and never against a stale copy of it."""
    assert gv.main(["--check"]) == 0


def test_the_writer_is_deterministic() -> None:
    first = {k: gv.render(v) for k, v in gv.build().items()}
    second = {k: gv.render(v) for k, v in gv.build().items()}
    assert first == second


def test_every_port_has_a_file_and_every_case_has_the_three_parts() -> None:
    files = sorted(p.name for p in (ROOT / "worker" / "golden").glob("*.json"))
    assert files == [
        "act.json",
        "assist.json",
        "fhir_emit.json",
        "followups.json",
        "healthcard.json",
        "helpers.json",
        "labels.json",
        "regions.json",
        "walks.json",
    ]
    total = 0
    for name in files:
        doc = json.loads((ROOT / "worker" / "golden" / name).read_text(encoding="utf-8"))
        assert doc["generated_by"] == "evals/golden_vectors.py"
        for key, value in doc.items():
            if not isinstance(value, list):
                continue
            for c in value:
                assert set(c) == {"name", "input", "expected"}, (name, key)
                total += 1
    assert total >= 60


def test_the_emitter_vectors_reach_the_hashed_id_and_a_whole_number() -> None:
    """The two places a port is most likely to drift: fhir_id past 64 characters, and the way
    Python prints a whole float in a narrative."""
    doc = json.loads((ROOT / "worker" / "golden" / "fhir_emit.json").read_text(encoding="utf-8"))
    long_case = next(c for c in doc["cases"] if c["name"].startswith("long id"))
    assert len(long_case["expected"]["id"]) == 64
    narratives = json.dumps(long_case["expected"])
    assert "1.0 metre" in narratives, "Python prints a whole float with .0"
    assert "&lt;bridge&gt; &amp; a" in narratives, "narrative text is escaped"
