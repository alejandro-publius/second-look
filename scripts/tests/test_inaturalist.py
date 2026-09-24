"""The iNaturalist context line is context and nothing more (UPDATE_29 section 8).

Nothing that decides can reach it: the gate and the follow-up rules import nothing of it, and the
code that serves it imports nothing that reaches them, in Python and in the Worker. The guided
check and the two-minute test never import the component that shows it. The two servers answer
in the same shape, and the page has the exact words for when nothing is on record.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "worker" / "src"
WEB = ROOT / "apps" / "web"
DECIDERS = ("core.gate", "core.followups", "apps.api.check", "apps.api.core_calls")
IMPORT_RE = re.compile(r"""^\s*(?:import|export)\b[^;]*?\bfrom\s+["']([^"']+)["']""", re.M | re.S)


def loaded_by(module: str) -> set[str]:
    """Every module Python loads to import this one, in a fresh interpreter."""
    code = f"import sys, {module}; print('\\n'.join(sorted(sys.modules)))"
    done = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return set(done.stdout.split())


@pytest.mark.parametrize("module", ["apps.api.inaturalist", "scripts.cache_inaturalist"])
def test_the_python_side_loads_nothing_that_decides(module: str) -> None:
    loaded = loaded_by(module)
    assert module in loaded
    assert not loaded & set(DECIDERS), loaded & set(DECIDERS)


@pytest.mark.parametrize(
    "path",
    [
        "core/gate.py",
        "core/followups.py",
        "apps/api/core_calls.py",
        "worker/src/core/followups.ts",
        "worker/src/check.ts",
    ],
)
def test_nothing_that_decides_mentions_it(path: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8").lower()
    assert "inaturalist" not in text and "inat_" not in text


def resolve(spec: str, here: Path, web: bool) -> Path | None:
    if spec.startswith("@/") and web:
        base = WEB / spec[2:]
    elif spec.startswith("."):
        base = (here.parent / spec).resolve()
    else:
        return None  # a package, not our code
    for cand in (base, *(base.with_name(base.name + ext) for ext in (".ts", ".tsx", ".mjs"))):
        if cand.is_file():
            return cand
    for ext in (".ts", ".tsx"):
        index = base / f"index{ext}"
        if index.is_file():
            return index
    return None


def reach(start: Path, *, web: bool = False) -> set[Path]:
    """Every file of ours that `start` imports, directly or through others."""
    seen: set[Path] = set()
    todo = [start]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        if f.suffix not in {".ts", ".tsx", ".mjs"}:
            continue
        for spec in IMPORT_RE.findall(f.read_text(encoding="utf-8")):
            found = resolve(spec, f, web)
            if found is not None:
                todo.append(found)
    return seen


def test_the_walker_follows_imports_it_should() -> None:
    """A walker that found nothing would pass everything below."""
    names = {p.name for p in reach(WORKER / "check.ts")}
    assert {"followups.ts", "regions.ts", "content.json"} <= names
    web = {p.name for p in reach(WEB / "components" / "SpotRecord.tsx", web=True)}
    assert {"InatContext.tsx", "api.ts", "t.ts"} <= web


def test_the_worker_route_reaches_nothing_that_decides() -> None:
    names = {p.relative_to(WORKER).as_posix() for p in reach(WORKER / "inaturalist.ts")}
    assert "core/regions.ts" in names
    assert not names & {"check.ts", "city.ts", "core/followups.ts", "core/fhir_emit.ts"}, names


@pytest.mark.parametrize(
    "page",
    ["app/check/page.tsx", "app/quick/page.tsx", "app/t/page.tsx", "app/demo/page.tsx"],
)
def test_the_guided_check_and_the_test_never_import_the_line(page: str) -> None:
    names = {p.name for p in reach(WEB / page, web=True)}
    assert len(names) > 3, "the walker should find the page's components"
    assert "InatContext.tsx" not in names


def test_only_the_record_and_the_city_show_the_line() -> None:
    users = sorted(
        p.relative_to(WEB).as_posix()
        for p in [*(WEB / "components").rglob("*.tsx"), *(WEB / "app").rglob("*.tsx")]
        if p.name != "InatContext.tsx" and "InatContext" in p.read_text(encoding="utf-8")
    )
    assert users == ["components/CityView.tsx", "components/SpotRecord.tsx"]


def ts_keys() -> set[str]:
    text = (WORKER / "inaturalist.ts").read_text(encoding="utf-8")
    body = text.split("export async function inaturalistView", 1)[1].split("  return {", 1)[1]
    body = body.split("\n  };", 1)[0]
    return set(re.findall(r"^\s{4}(\w+)[:,]", body, re.M))


def test_the_two_servers_answer_in_the_same_shape() -> None:
    py = (ROOT / "apps" / "api" / "inaturalist.py").read_text(encoding="utf-8")
    body = py.split("def inaturalist_view", 1)[1]
    py_keys = set(re.findall(r'^\s{8}"(\w+)":', body, re.M))
    assert (
        py_keys
        == ts_keys()
        == {
            "creek",
            "shown",
            "status",
            "fetched_at",
            "since",
            "radius_m",
            "species",
            "source",
            "terms",
        }
    )


def test_the_page_has_the_exact_words_for_nothing_on_record() -> None:
    locale = json.loads((ROOT / "content" / "locales" / "en.json").read_text(encoding="utf-8"))
    assert "no recent sightings on record" in locale["inat.none"]
    component = (WEB / "components" / "InatContext.tsx").read_text(encoding="utf-8")
    assert 't("inat.none")' in component


def test_no_species_or_place_reaches_the_browser() -> None:
    """The credits page gets three facts per photo. A test photo's species is its answer."""
    if shutil.which("node") is None:
        pytest.skip("needs node")
    doc = json.loads((ROOT / "results" / "inat_photos.json").read_text(encoding="utf-8"))
    body = (
        "import { inatChecks } from './scripts/inat-checks.mjs';"
        "const raw = JSON.parse(process.argv[1]);"
        "const shown = new Set(raw.photos.map((p) => p.photo_id).slice(1));"
        "process.stdout.write(JSON.stringify(inatChecks(raw, shown)));"
    )
    done = subprocess.run(
        ["node", "--input-type=module", "-e", body, json.dumps(doc)],
        cwd=WEB,
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(done.stdout)
    assert out["checked_at"] == doc["checked_at"]
    assert len(out["photos"]) == len(doc["photos"]) - 1, "only photos the site shows"
    for got in out["photos"].values():
        assert set(got) == {"found", "research_grade", "in_california"}
    for p in doc["photos"]:
        assert p["taxon"] not in done.stdout and p["place_guess"] not in done.stdout


def test_the_words_say_the_gate_is_per_creek_not_per_person() -> None:
    """REVIEW_03 R07. The route opens the line for a creek once any finished check there has
    answered the invasive plant question, and nothing checks who is looking, so a later volunteer
    can see it before their own answer. The words must say that, and must not promise more.
    worker/test/e2e.mjs proves the behaviour with a viewer that has checked nothing."""
    flat = {
        path: " ".join((ROOT / path).read_text(encoding="utf-8").split())
        for path in (
            "worker/src/inaturalist.ts",
            "apps/api/inaturalist.py",
            "docs/adr/0011-inaturalist-context.md",
            "README.md",
        )
    }
    for path, text in flat.items():
        assert "lead anyone's answer" not in text, path
        assert "never before the invasive plant question is answered" not in text, path
    for path in ("worker/src/inaturalist.ts", "apps/api/inaturalist.py"):
        assert "The gate is per creek, not per person" in flat[path], path
        assert "a later volunteer who has not checked this creek yet included" in flat[path], path
    assert (
        "The gate opens once for the creek, not for each person"
        in flat["docs/adr/0011-inaturalist-context.md"]
    )
    assert "once a finished check on that creek has answered" in flat["README.md"]
