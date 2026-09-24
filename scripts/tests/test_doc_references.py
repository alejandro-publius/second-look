"""Every file, test and make target the engineering docs name really exists.

WRITEUP.md, SECURITY.md, DEPLOY.md, docs/API.md, docs/MCP.md and docs/adr/ say "this file proves
it" and "this test fails if it breaks". A renamed test or a moved file would leave such a sentence
pointing at nothing, and the claim would still read as true. So every `path` and every
`path::test_name` in backticks is checked here, and so is every `make <target>`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = [
    ROOT / "WRITEUP.md",
    ROOT / "SECURITY.md",
    ROOT / "DEPLOY.md",
    ROOT / "docs" / "API.md",
    ROOT / "docs" / "MCP.md",
    ROOT / "docs" / "DATA_CARD.md",
    ROOT / "docs" / "MODEL_CARD.md",
    ROOT / "docs" / "THREAT_MODEL.md",
    *sorted((ROOT / "docs" / "adr").glob("*.md")),
]
PATH_RE = re.compile(r"`([A-Za-z0-9_.\[\]-]+(?:/[A-Za-z0-9_.\[\]-]+)+/?)(?:::(\w+))?`")
MAKE_RE = re.compile(r"`make ([a-z][a-z0-9-]*)")
# Made at run time, outside git, or on another machine: named in the docs, never in the repo.
NOT_IN_GIT = ("data/", "apps/web/out", "fhir/build", "docs/video/clips", "node_modules/")


def references(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for m in PATH_RE.finditer(text):
        path, test = m.group(1).removeprefix("./"), m.group(2)
        if path.startswith(NOT_IN_GIT):
            continue
        # A folder is written with a slash at the end, `worker/golden/`; words such as `yes/no`
        # have neither a slash at the end nor a file extension, and are not paths.
        if "." not in path and not test and not path.endswith("/"):
            continue
        out.append((path, test))
    return out


def test_every_doc_exists() -> None:
    for doc in DOCS[:5]:
        assert doc.exists(), doc
    assert len(DOCS) > 5, "docs/adr/ has no records"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_every_named_file_and_test_exists(doc: Path) -> None:
    text = doc.read_text(encoding="utf-8")
    missing: list[str] = []
    for path, test in references(text):
        target = ROOT / path.rstrip("/")
        if not target.exists():
            missing.append(path)
            continue
        if test:
            source = target.read_text(encoding="utf-8")
            if not re.search(rf"^(?:async )?def {re.escape(test)}\(", source, re.M):
                missing.append(f"{path}::{test}")
    assert missing == [], f"{doc.name} names what does not exist"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_every_named_make_target_exists(doc: Path) -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = set(re.findall(r"^([a-z][a-z0-9-]*):", makefile, re.M))
    named = set(MAKE_RE.findall(doc.read_text(encoding="utf-8")))
    assert named - targets == set(), f"{doc.name} names make targets that do not exist"


def test_the_reader_sees_paths_tests_and_skips_words() -> None:
    text = (
        "`core/gate.py`, `core/tests/test_gate.py::test_one`, `worker/golden/`, "
        "`data/demo`, `./data/uploads`, `/api/two`, `yes/no`, `Bundle/<visit id>`"
    )
    assert references(text) == [
        ("core/gate.py", None),
        ("core/tests/test_gate.py", "test_one"),
        ("worker/golden/", None),
    ]
