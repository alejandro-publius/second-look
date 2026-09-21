"""The picks files go in, photos come out, and every refusal and swap is named.

No test here touches a real API. Every request is mocked.
"""

from __future__ import annotations

import csv
from pathlib import Path

import httpx
import pytest
import respx

from scripts.batch_fetch_photos import PicksError, read_picks, run
from scripts.find_open_photos import COMMONS_API
from scripts.tests.test_fetch_open_photo import (
    jpeg_bytes,
    repo,  # noqa: F401  the fixture that builds a repo with a manifest and a region pack
    rows,
)
from scripts.tests.test_find_open_photos import commons_page, commons_payload

PICK_COLUMNS = ["url", "feature", "role", "side", "scene", "notes", "label", "evidence"]


def page_url(name: str) -> str:
    return f"https://commons.wikimedia.org/wiki/File:{name}"


def write_picks(folder: Path, feature: str, picks: list[tuple[str, str, str]]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"picks-{feature}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PICK_COLUMNS)
        writer.writeheader()
        for name, role, label in picks:
            writer.writerow(
                {
                    "url": page_url(name),
                    "feature": feature,
                    "role": role,
                    "side": label,
                    "scene": "",
                    "notes": "",
                    "label": label,
                    "evidence": "",
                }
            )


def mock_file(name: str, licence: str = "cc-by-4.0", image_ok: bool = True) -> None:
    under = name.replace(" ", "_")
    respx.get(COMMONS_API, params__contains={"titles": f"File:{name}"}).mock(
        return_value=httpx.Response(200, json=commons_payload(commons_page(name, licence)))
    )
    image = f"https://upload.wikimedia.org/wikipedia/commons/a/aa/{under}"
    respx.get(image).mock(
        return_value=httpx.Response(
            200, content=jpeg_bytes(), headers={"content-type": "image/jpeg"}
        )
        if image_ok
        else httpx.Response(404)
    )


@respx.mock
def test_every_picked_photo_lands_and_spares_stay_on_the_shelf(repo: Path) -> None:  # noqa: F811
    folder = repo / "photos" / "candidates"
    write_picks(
        folder,
        "artificial_bank",
        [("A.jpg", "test", "present"), ("B.jpg", "test", "absent"), ("C.jpg", "spare", "present")],
    )
    for name in ("A.jpg", "B.jpg", "C.jpg"):
        mock_file(name)

    assert run(folder, repo) == 0
    got = rows(repo)
    assert [r["source_url"] for r in got] == [page_url("A.jpg"), page_url("B.jpg")]
    assert [r["gold_label"] for r in got] == ["present", "absent"]
    assert [r["id"] for r in got] == ["ph-bank-01", "ph-bank-02"], "readable ids, one per feature"


@respx.mock
def test_a_failed_download_takes_the_spare_of_the_same_feature_and_label(repo: Path) -> None:  # noqa: F811
    folder = repo / "photos" / "candidates"
    write_picks(
        folder,
        "artificial_bank",
        [("A.jpg", "test", "present"), ("Spare.jpg", "spare", "present")],
    )
    mock_file("A.jpg", image_ok=False)
    mock_file("Spare.jpg")

    assert run(folder, repo) == 1, "a refusal is worth a non zero exit even when a spare covered it"
    got = rows(repo)
    assert len(got) == 1
    assert got[0]["source_url"] == page_url("Spare.jpg")
    assert got[0]["role"] == "test" and got[0]["gold_label"] == "present"


@respx.mock
def test_a_failure_with_no_spare_of_that_label_leaves_the_slot_short(repo: Path) -> None:  # noqa: F811
    folder = repo / "photos" / "candidates"
    write_picks(
        folder,
        "artificial_bank",
        [("A.jpg", "test", "present"), ("Spare.jpg", "spare", "absent")],
    )
    mock_file("A.jpg", image_ok=False)
    mock_file("Spare.jpg")

    assert run(folder, repo) == 1
    assert rows(repo) == [], "an absent spare never stands in for a present slot"


@respx.mock
def test_the_warm_up_pair_carries_no_gold_label(repo: Path) -> None:  # noqa: F811
    folder = repo / "photos" / "candidates"
    write_picks(folder, "warmup", [("W1.jpg", "warmup", ""), ("W2.jpg", "warmup", "")])
    mock_file("W1.jpg")
    mock_file("W2.jpg")

    assert run(folder, repo) == 0
    got = rows(repo)
    assert [r["gold_label"] for r in got] == ["", ""]
    assert [r["feature"] for r in got] == ["", ""], "the warm-up belongs to no feature"


def test_a_dry_run_downloads_nothing(repo: Path) -> None:  # noqa: F811
    folder = repo / "photos" / "candidates"
    write_picks(folder, "artificial_bank", [("A.jpg", "test", "present")])
    assert run(folder, repo, dry_run=True) == 0
    assert rows(repo) == []


def test_picks_files_are_refused_before_anything_downloads(repo: Path) -> None:  # noqa: F811
    folder = repo / "photos" / "candidates"
    with pytest.raises(PicksError, match="no picks"):
        read_picks(folder)

    write_picks(folder, "artificial_bank", [("A.jpg", "test", "maybe")])
    with pytest.raises(PicksError, match="label"):
        read_picks(folder)
