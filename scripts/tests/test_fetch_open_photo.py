"""One chosen photo goes through the normal ingest and lands with its evidence, or not at all.

No test here touches a real API. Every request is mocked.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from PIL import Image

from scripts import check_manifest
from scripts.fetch_open_photo import FetchError, coarse_place, fetch
from scripts.find_open_photos import COMMONS_API, INAT_API, RateLimit
from scripts.ingest_photos import MANIFEST_COLUMNS
from scripts.tests.test_find_open_photos import commons_page, commons_payload, inat_observation

COMMONS_URL = "https://commons.wikimedia.org/wiki/File:Bank.jpg"
COMMONS_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/a/aa/Bank.jpg"
INAT_URL = "https://www.inaturalist.org/observations/4321"
INAT_IMAGE = "https://inaturalist-open-data.s3.amazonaws.com/photos/4321/original.jpeg"
ARUNDO_LINK = "https://www.cal-ipc.org/plants/profile/arundo-donax-profile/"
REGION_PACK = """
region: california-bay-area
invasive_plants:
  - common_name: "Giant reed"
    latin_name: "Arundo donax"
    cal_ipc_rating: "High"
    source: "https://www.cal-ipc.org/plants/profile/arundo-donax-profile/"
"""


def jpeg_bytes(size: tuple[int, int] = (2000, 1400)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (110, 120, 130)).save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "photos").mkdir(parents=True)
    with (root / "photos" / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS).writeheader()
    pack = root / "content" / "drafts" / "regions"
    pack.mkdir(parents=True)
    (pack / "california-bay-area.yaml").write_text(REGION_PACK, encoding="utf-8")
    return root


def rows(root: Path) -> list[dict[str, str]]:
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mock_commons(licence: str, **page: Any) -> None:
    payload = commons_payload(commons_page("Bank.jpg", licence, **page))
    respx.get(COMMONS_API).mock(return_value=httpx.Response(200, json=payload))
    respx.get(COMMONS_IMAGE).mock(
        return_value=httpx.Response(
            200, content=jpeg_bytes(), headers={"content-type": "image/jpeg"}
        )
    )


def mock_inat(**observation: Any) -> None:
    payload = {"results": [inat_observation(**observation)]}
    respx.get(f"{INAT_API}/4321").mock(return_value=httpx.Response(200, json=payload))
    respx.get(INAT_IMAGE).mock(
        return_value=httpx.Response(
            200, content=jpeg_bytes(), headers={"content-type": "image/jpeg"}
        )
    )


def run(
    url: str,
    repo: Path,
    feature: str = "artificial_bank",
    role: str = "test",
    gold_label: str = "",
) -> Any:
    return fetch(url, feature, role, gold_label=gold_label, root=repo, limiter=RateLimit(0.0))


@respx.mock
def test_a_fetched_photo_writes_a_manifest_row_with_its_evidence(repo: Path) -> None:
    mock_commons("cc-by-4.0")
    row = run(COMMONS_URL, repo)

    assert row["id"] == "ph-open-01"
    assert (repo / "photos" / row["file"]).is_file()
    assert row["author"] == "Jo Rivers"
    assert row["license"] == "CC-BY-4.0"
    assert row["source_url"] == COMMONS_URL
    assert "Concrete lined channel on a city creek" in row["label_evidence"]
    assert "Commons categories: Riprap, Creeks of California" in row["label_evidence"]
    assert row["gold_label"] == "", "a person labels, never this script"
    assert row["synthetic"] == "false" and row["faces"] == "false"
    assert rows(repo) == [row]
    with Image.open(repo / "photos" / row["file"]) as img:
        assert max(img.size) <= 1600, "ingest did the resizing, so there is one ingest path"
        assert dict(img.getexif()) == {}


@respx.mock
def test_a_licence_we_may_not_use_is_refused(repo: Path) -> None:
    mock_commons("cc-by-nc-4.0")
    before = (repo / "photos" / "manifest.csv").read_bytes()
    with pytest.raises(FetchError) as caught:
        run(COMMONS_URL, repo)
    assert "CC0, CC BY or CC BY-SA" in str(caught.value)
    assert (repo / "photos" / "manifest.csv").read_bytes() == before
    assert rows(repo) == []


@respx.mock
def test_a_licence_version_the_manifest_cannot_record_is_refused(repo: Path) -> None:
    """CC BY 1.0 is real and open, but the allowlist has no entry, so we refuse rather than
    write it down as a version it is not."""
    mock_commons("cc-by-1.0")
    with pytest.raises(FetchError) as caught:
        run(COMMONS_URL, repo)
    assert "CC BY 1.0" in str(caught.value)
    assert rows(repo) == []


@respx.mock
def test_an_older_version_we_do_allow_is_written_down_as_that_version(repo: Path) -> None:
    """Update 09 follow up: refusing 2.0 and 3.0 halved the pool for no gain to anyone."""
    mock_commons("cc-by-sa-3.0")
    run(COMMONS_URL, repo)
    written = rows(repo)
    assert len(written) == 1
    assert written[0]["license"] == "CC-BY-SA-3.0"
    assert written[0]["author"]


@respx.mock
def test_a_record_that_is_not_research_grade_is_refused(repo: Path) -> None:
    mock_inat(quality_grade="casual")
    with pytest.raises(FetchError) as caught:
        run(INAT_URL, repo, feature="invasive_plant")
    assert "research grade" in str(caught.value)
    assert rows(repo) == []


@respx.mock
def test_a_research_grade_plant_row_carries_the_cal_ipc_link(repo: Path) -> None:
    mock_inat()
    row = run(INAT_URL, repo, feature="invasive_plant")

    assert row["license"] == "CC-BY-4.0"
    assert row["author"] == "Sam Willow"
    assert row["source_url"] == INAT_URL
    assert "research grade" in row["label_evidence"]
    assert "community identification Arundo donax" in row["label_evidence"]
    assert ARUNDO_LINK in row["label_evidence"]
    assert row["capture_date"] == "2026-05-04"
    assert row["coarse_location"] == "Berkeley, CA, USA"
    assert row["scene_id"] == "inat-4321"


@respx.mock
def test_a_plant_that_is_not_on_the_cal_ipc_inventory_is_refused(repo: Path) -> None:
    mock_inat(taxon="Tradescantia fluminensis")
    with pytest.raises(FetchError) as caught:
        run(INAT_URL, repo, feature="invasive_plant")
    assert "Cal-IPC" in str(caught.value)
    assert rows(repo) == []


@respx.mock
def test_something_that_is_not_an_image_is_refused(repo: Path) -> None:
    payload = commons_payload(commons_page("Bank.jpg", "cc0"))
    respx.get(COMMONS_API).mock(return_value=httpx.Response(200, json=payload))
    respx.get(COMMONS_IMAGE).mock(
        return_value=httpx.Response(200, content=b"<html>", headers={"content-type": "text/html"})
    )
    with pytest.raises(FetchError) as caught:
        run(COMMONS_URL, repo)
    assert "not a JPEG or PNG" in str(caught.value)
    assert rows(repo) == []


def test_a_place_name_stays_coarse() -> None:
    assert coarse_place("Under the bridge, Strawberry Creek, Berkeley, CA, USA") == (
        "Berkeley, CA, USA"
    )
    assert coarse_place("") == ""


@respx.mock
def test_the_manifest_check_knows_the_new_column(repo: Path) -> None:
    mock_commons("cc-by-4.0")
    # A lesson role, because the mocked page sits in the Commons category Riprap and laid stone
    # is not allowed in the test role.
    run(COMMONS_URL, repo, role="lesson")
    assert check_manifest.main(repo) == 0

    # Same row, evidence wiped: a photo from a source has to say what backs its label.
    with (repo / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        kept = list(csv.DictReader(f))
    for row in kept:
        row["label_evidence"] = ""
    with (repo / "photos" / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(kept)
    assert check_manifest.main(repo) == 1


@respx.mock
def test_a_plant_row_without_a_cal_ipc_link_fails_the_manifest_check(repo: Path) -> None:
    mock_inat()
    run(INAT_URL, repo, feature="invasive_plant")
    assert check_manifest.main(repo) == 0

    with (repo / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        kept = list(csv.DictReader(f))
    for row in kept:
        row["label_evidence"] = "somebody said it looked like giant reed"
    with (repo / "photos" / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(kept)
    assert check_manifest.main(repo) == 1


def test_every_row_in_the_repo_manifest_is_still_valid() -> None:
    assert check_manifest.main() == 0


@respx.mock
def test_the_label_chosen_while_picking_becomes_the_first_gold_label(repo: Path) -> None:
    """Update 11 section 5: the picker's label is the first gold label, not a guess by code."""
    mock_commons("cc-by-4.0")
    row = run(COMMONS_URL, repo, role="lesson", gold_label="present")
    assert row["gold_label"] == "present"
    assert check_manifest.main(repo) == 0


@respx.mock
def test_a_label_the_manifest_cannot_hold_is_refused_before_anything_downloads(repo: Path) -> None:
    mock_commons("cc-by-4.0")
    with pytest.raises(FetchError) as caught:
        run(COMMONS_URL, repo, gold_label="damaged_but_tidy")
    assert "gold_label" in str(caught.value)
    assert rows(repo) == []


@respx.mock
def test_a_native_look_alike_labelled_absent_needs_no_cal_ipc_link(repo: Path) -> None:
    """A plant photo labelled absent says no listed species is in it, so there is no profile page
    to point at. Demanding one ruled out every native look-alike the test needs."""
    mock_inat(taxon="Rubus ursinus")
    row = run(INAT_URL, repo, feature="invasive_plant", gold_label="absent")
    assert row["gold_label"] == "absent"
    assert "Rubus ursinus" in row["label_evidence"]
    assert "cal-ipc.org" not in row["label_evidence"]
    assert check_manifest.main(repo) == 0, "and the manifest check does not ask for one either"


@respx.mock
def test_a_plant_labelled_present_still_needs_the_cal_ipc_link(repo: Path) -> None:
    mock_inat(taxon="Rubus ursinus")
    with pytest.raises(FetchError) as caught:
        run(INAT_URL, repo, feature="invasive_plant", gold_label="present")
    assert "Cal-IPC" in str(caught.value)
    assert rows(repo) == []


@respx.mock
def test_a_public_domain_photo_is_fetched_and_recorded_as_public_domain(repo: Path) -> None:
    mock_commons("pd", artist="Environmental Protection Agency", copyrighted="False")
    row = run(COMMONS_URL, repo, role="lesson", gold_label="present")
    assert row["license"] == "public-domain"
    assert row["author"] == "Environmental Protection Agency"
    assert check_manifest.main(repo) == 0


@respx.mock
def test_laid_stone_in_the_test_role_fails_the_manifest_check(repo: Path) -> None:
    """The app gives laid stone a bank type of its own, so a test item has no one right answer."""
    mock_commons("cc-by-4.0", description="Gabion baskets holding the bank of a city creek")
    run(COMMONS_URL, repo, role="test", gold_label="present")
    assert check_manifest.main(repo) == 1


@respx.mock
def test_laid_stone_is_allowed_in_a_lesson_where_the_caption_can_say_so(repo: Path) -> None:
    mock_commons("cc-by-4.0", description="Gabion baskets holding the bank of a city creek")
    run(COMMONS_URL, repo, role="lesson", gold_label="present")
    assert check_manifest.main(repo) == 0
