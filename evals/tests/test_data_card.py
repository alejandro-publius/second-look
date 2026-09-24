"""The data card's counts: read from the manifests, and the committed file is what they say."""

from __future__ import annotations

import json
from pathlib import Path

from evals import data_card

HEADER = "id,role,feature,gold_label,labeller_2,label_evidence,source_url,license,synthetic,faces\n"


def fixture(tmp_path: Path, photo_rows: list[str]) -> Path:
    (tmp_path / "photos").mkdir()
    (tmp_path / "videos").mkdir()
    (tmp_path / "docs" / "video").mkdir(parents=True)
    (tmp_path / "photos" / "manifest.csv").write_text(HEADER + "".join(photo_rows))
    (tmp_path / "videos" / "manifest.csv").write_text(
        "id,country,label_value,source_url,license\n"
        "v1,Chile,,https://www.youtube.com/watch?v=a,CC BY\n"
        "v2,Chile,present,https://commons.wikimedia.org/wiki/File:b.webm,CC BY-SA 4.0\n"
        "v3,,,https://example.org/c,CC0\n"
    )
    (tmp_path / "docs" / "video" / "footage.csv").write_text(
        "kind,source_page,licence\nvideo,https://commons.wikimedia.org/wiki/File:c.webm,CC0\n"
    )
    return tmp_path


def test_the_committed_file_is_what_the_manifests_say() -> None:
    committed = json.loads(data_card.OUT.read_text(encoding="utf-8"))
    assert committed == data_card.build(), "run: uv run python evals/data_card.py"
    assert data_card.main(["--check"]) == 0


def test_labels_are_counted_per_role_and_feature_and_blank_is_unlabelled(tmp_path: Path) -> None:
    root = fixture(
        tmp_path,
        [
            "a,test,pipe_running,present,,says a pipe,https://commons.wikimedia.org/wiki/F,CC0,false,false\n",
            "b,test,pipe_running,absent,present,says none,https://www.inaturalist.org/o/1,CC0,false,false\n",
            "c,test,invasive_plant, ,,,https://www.inaturalist.org/o/2,CC-BY-4.0,false,false\n",
            "d,benchmark,,,,frame,https://www.youtube.com/watch?v=x,CC-BY-3.0,FALSE,true\n",
            "e,poster,,,,,,CC0,true,false\n",
        ],
    )
    doc = data_card.build(root)
    photos = doc["photos"]
    assert photos["rows"] == 5
    assert photos["labelled"] == 2
    assert photos["with_second_label"] == 1
    assert photos["with_label_evidence"] == 3
    assert photos["marked_synthetic"] == 1
    assert photos["marked_with_faces"] == 1
    assert photos["other_roles"] == ["poster"]
    test = photos["test"]
    assert (test["rows"], test["labelled"], test["unlabelled"]) == (3, 2, 1)
    assert (test["present"], test["absent"]) == (1, 1)
    assert test["per_feature"] == {"pipe_running": {"absent": 1, "present": 1}}
    assert test["by_source"] == {"Wikimedia Commons": 1, "iNaturalist": 2}
    assert photos["benchmark"]["labelled"] == 0
    assert photos["benchmark"]["by_source"] == {"YouTube": 1}
    assert photos["warmup"]["rows"] == 0
    assert photos["by_source"]["unknown"] == 1


def test_videos_and_film_footage_are_counted_from_their_own_files(tmp_path: Path) -> None:
    doc = data_card.build(fixture(tmp_path, []))
    videos = doc["videos"]
    assert (videos["rows"], videos["labelled"], videos["countries"]) == (3, 1, 1)
    assert videos["by_source"] == {"Wikimedia Commons": 1, "YouTube": 1, "example.org": 1}
    assert doc["film_footage"] == {
        "rows": 1,
        "by_kind": {"video": 1},
        "by_source": {"Wikimedia Commons": 1},
        "by_licence": {"CC0": 1},
    }
    assert doc["real"] is True and doc["synthetic"] is False


def test_check_fails_when_the_committed_file_is_stale(tmp_path: Path, monkeypatch) -> None:
    stale = tmp_path / "data_card.json"
    stale.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(data_card, "OUT", stale)
    assert data_card.main(["--check"]) == 1
