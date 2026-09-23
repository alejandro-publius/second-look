"""The pick rule: a name is not a label, and a video whose frames failed is picked again."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("pick_videos", ROOT / "scripts" / "pick_videos.py")
assert spec and spec.loader
pick_videos = importlib.util.module_from_spec(spec)
sys.modules["pick_videos"] = pick_videos
spec.loader.exec_module(pick_videos)


def test_a_project_called_concrete_creek_is_not_a_built_bank() -> None:
    text = "the project was named: concrete creek, reclamation of a stream via art."
    assert pick_videos.label_for(text, text) == ("", "", "")


def test_riprap_in_the_description_is_a_built_bank() -> None:
    text = "crews placed riprap along the eroding bank of the creek."
    feature, value, evidence = pick_videos.label_for(text, text)
    assert (feature, value) == ("artificial_bank", "present")
    assert "riprap" in evidence


def test_a_plant_label_never_comes_from_a_description() -> None:
    text = "japanese knotweed has taken over the stream bank."
    assert pick_videos.label_for(text, text) == ("", "", "")
    assert all(feature != "invasive_plant" for feature, _, _ in pick_videos.LABEL_RULES)


def test_a_phrase_found_only_in_the_title_is_quoted_as_the_title() -> None:
    title = "Walking the Concrete Channel of the Arroyo"
    feature, value, evidence = pick_videos.label_for(title, "A short walk on a sunny day.")
    assert (feature, value) == ("artificial_bank", "present")
    assert evidence == 'The title says: "Walking the Concrete Channel of the Arroyo"'


def test_a_phrase_in_the_description_is_quoted_as_the_description() -> None:
    description = "A walk. The creek runs in a concrete channel here."
    _, _, evidence = pick_videos.label_for("Concrete channel walk", description)
    assert evidence == 'The description says: "The creek runs in a concrete channel here."'


def test_a_phrase_split_between_title_and_description_is_no_evidence() -> None:
    assert pick_videos.label_for("Along the concrete", "channel of the creek") == ("", "", "")


def _candidate(url: str, title: str = "Creek walk") -> dict[str, object]:
    return {
        "id": url.rsplit("=", 1)[-1],
        "source": "youtube",
        "title": title,
        "author": "someone",
        "licence": "Creative Commons Attribution license (reuse allowed)",
        "duration_s": 300,
        "height": 1080,
        "country_if_stated": "",
        "url": url,
        "query": "creek walk",
        "description_excerpt": "a walk along the creek",
    }


def test_a_video_whose_frames_failed_is_dropped_and_another_is_picked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    videos = tmp_path / "videos"
    videos.mkdir()
    a, b = "https://www.youtube.com/watch?v=aaa", "https://www.youtube.com/watch?v=bbb"
    (videos / "candidates.json").write_text(json.dumps([_candidate(a), _candidate(b)]))
    (videos / "failed_videos.json").write_text(json.dumps({a: "only 2 of 40 kept"}))
    for name in ("VIDEOS", "CANDIDATES", "MANIFEST", "PICKED", "FAILURES"):
        attr = {
            "VIDEOS": videos,
            "CANDIDATES": videos / "candidates.json",
            "MANIFEST": videos / "manifest.csv",
            "PICKED": videos / "picked.json",
            "FAILURES": videos / "failed_videos.json",
        }[name]
        monkeypatch.setattr(pick_videos, name, attr)
    assert pick_videos.main(["--offline", "--wanted", "2"]) == 0
    picked = json.loads((videos / "picked.json").read_text())
    assert [k["id"] for k in picked["kept"]] == ["bbb"]
    dropped = {d["id"]: d["why"] for d in picked["dropped"]}
    assert dropped["aaa"].startswith("frames: only 2 of 40")


def test_a_longer_place_name_wins_over_the_country_inside_it() -> None:
    assert pick_videos.place_country("a creek in new mexico")[0] == "United States"
    assert pick_videos.place_country("blue mountains, new south wales")[0] == "Australia"
    assert pick_videos.place_country("a brook in wales")[0] == "United Kingdom"
    assert pick_videos.place_country("the ruhr, deutschland")[0] == "Germany"


def test_a_specific_place_wins_over_a_country_name_elsewhere_in_the_text() -> None:
    oregon = "a creek in oregon, with a pair of canada geese on the bank"
    assert pick_videos.place_country(oregon) == (
        "United States",
        "the title or description says 'oregon'",
    )
    for place, country in pick_videos.SPECIFIC_PLACES:
        for name, _ in pick_videos.COUNTRY_NAMES:
            got = pick_videos.place_country(f"{name} then {place}")[0]
            assert got == country, f"{place!r} lost to the country name {name!r}"


def test_every_bare_country_name_sits_after_every_specific_place() -> None:
    names = {name for name, _ in pick_videos.COUNTRY_NAMES}
    order = [place for place, _ in pick_videos.PLACES]
    first_country = min(order.index(n) for n in names)
    assert all(p in names for p in order[first_country:])


# The label list in docs/REAL_VS_SYNTHETIC.md: one bullet per feature and value, which may wrap
# onto indented lines, with every phrase in backticks.
DOC = ROOT / "docs" / "REAL_VS_SYNTHETIC.md"
BULLET = re.compile(r"^- \*\*(\w+) (present|absent)\*\*")


def test_the_doc_lists_exactly_the_label_phrases_the_code_uses() -> None:
    text = DOC.read_text(encoding="utf-8")
    documented: dict[tuple[str, str], set[str]] = {}
    key: tuple[str, str] | None = None
    for line in text.splitlines():
        match = BULLET.match(line)
        if match:
            key = (match.group(1), match.group(2))
            documented[key] = set()
        elif not line.startswith("  "):
            key = None
        if key is not None:
            documented[key] |= set(re.findall(r"`([^`]+)`", line))
    in_code = {(f, v): set(phrases) for f, v, phrases in pick_videos.LABEL_RULES}
    assert documented == in_code
    assert "No plant label ever comes from a description" in text
