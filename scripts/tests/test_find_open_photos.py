"""The search only keeps photos we may use: allowed licence, research grade, named author.

No test here touches a real API. Every request is mocked.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import respx

from scripts.find_open_photos import (
    COMMONS_API,
    INAT_API,
    USER_AGENT,
    Candidate,
    Licence,
    RateLimit,
    Search,
    licence_from_commons,
    licence_from_inat,
    run_search,
    sheet_html,
    write_sheet,
)

COMMONS_SEARCH = Search("commons", "riprap stream bank", "present")
INAT_SEARCH = Search("inat_taxon", "Arundo donax", "present")
CAL_IPC = {
    "arundo donax": {
        "latin_name": "Arundo donax",
        "common_name": "Giant reed",
        "rating": "High",
        "link": "https://www.cal-ipc.org/plants/profile/arundo-donax-profile/",
    }
}


def commons_page(
    name: str,
    licence: str,
    artist: str = "Jo Rivers",
    description: str = "Concrete lined channel on a city creek",
) -> dict[str, Any]:
    under = name.replace(" ", "_")
    artist_html = f'<a href="/wiki/User:Jo" class="x">{artist}</a>' if artist else ""
    return {
        "pageid": abs(hash(name)) % 100000,
        "title": f"File:{name}",
        "imageinfo": [
            {
                "url": f"https://upload.wikimedia.org/wikipedia/commons/a/aa/{under}",
                "descriptionurl": f"https://commons.wikimedia.org/wiki/File:{under}",
                "thumburl": f"https://thumb.wikimedia.org/thumb/{under}/320px-{under}",
                "user": "SomeUploader",
                "extmetadata": {
                    "License": {"value": licence},
                    "LicenseShortName": {"value": licence.upper()},
                    "Artist": {"value": artist_html},
                    "ImageDescription": {"value": f'<div class="description">{description}</div>'},
                    "Categories": {"value": "Riprap|Creeks of California"},
                },
            }
        ],
    }


def commons_payload(*pages: dict[str, Any]) -> dict[str, Any]:
    return {"batchcomplete": True, "query": {"pages": list(pages)}}


def inat_observation(
    obs_id: int = 4321,
    quality_grade: str = "research",
    license_code: str = "cc-by",
    taxon: str = "Arundo donax",
) -> dict[str, Any]:
    return {
        "id": obs_id,
        "quality_grade": quality_grade,
        "uri": f"https://www.inaturalist.org/observations/{obs_id}",
        "taxon": {"name": taxon, "preferred_common_name": "giant reed"},
        "user": {"login": "creekwatcher", "name": "Sam Willow"},
        "place_guess": "Strawberry Creek, Berkeley, CA, USA",
        "observed_on": "2026-05-04",
        "num_identification_agreements": 3,
        "photos": [
            {
                "id": obs_id,
                "license_code": license_code,
                "url": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{obs_id}/square.jpeg",
                "attribution": "(c) Sam Willow, some rights reserved (CC BY)",
            }
        ],
    }


def client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT})


def search_commons(payload: dict[str, Any]) -> list[Candidate]:
    respx.get(COMMONS_API).mock(return_value=httpx.Response(200, json=payload))
    with client() as c:
        return run_search(c, RateLimit(0.0), COMMONS_SEARCH, "artificial_bank", {}, 20)


def search_inat(payload: dict[str, Any]) -> list[Candidate]:
    respx.get(INAT_API).mock(return_value=httpx.Response(200, json=payload))
    with client() as c:
        return run_search(c, RateLimit(0.0), INAT_SEARCH, "invasive_plant", CAL_IPC, 20)


def test_user_agent_names_the_project_and_a_contact() -> None:
    assert "Second Look" in USER_AGENT
    assert "contact" in USER_AGENT and "@" in USER_AGENT


@respx.mock
def test_a_licence_we_may_not_use_is_dropped() -> None:
    got = search_commons(
        commons_payload(
            commons_page("Keep_cc0.jpg", "cc0"),
            commons_page("Keep_by.jpg", "cc-by-4.0"),
            commons_page("Keep_bysa.jpg", "cc-by-sa-3.0"),
            commons_page("Drop_nc.jpg", "cc-by-nc-4.0"),
            commons_page("Drop_ncsa.jpg", "cc-by-nc-sa-2.0"),
            commons_page("Drop_nd.jpg", "cc-by-nd-4.0"),
            commons_page("Drop_pd.jpg", "pd"),
            commons_page("Drop_fairuse.jpg", "fair use"),
            commons_page("Drop_empty.jpg", ""),
        )
    )
    kept = [c.title for c in got]
    assert kept == ["File:Keep_cc0.jpg", "File:Keep_by.jpg", "File:Keep_bysa.jpg"]
    assert not [c for c in got if "Drop" in c.title]


@respx.mock
def test_an_inaturalist_photo_under_a_licence_we_may_not_use_is_dropped() -> None:
    payload = {
        "results": [
            inat_observation(obs_id=1, license_code="cc-by-nc"),
            inat_observation(obs_id=2, license_code="cc-by-nc-sa"),
            inat_observation(obs_id=3, license_code=None),  # type: ignore[arg-type]
            inat_observation(obs_id=4, license_code="cc-by-sa"),
        ]
    }
    got = search_inat(payload)
    assert [c.page_url.rsplit("/", 1)[-1] for c in got] == ["4"]


@respx.mock
def test_a_record_that_is_not_research_grade_is_dropped() -> None:
    payload = {
        "results": [
            inat_observation(obs_id=11, quality_grade="casual"),
            inat_observation(obs_id=12, quality_grade="needs_id"),
            inat_observation(obs_id=13, quality_grade="research"),
        ]
    }
    got = search_inat(payload)
    assert [c.page_url.rsplit("/", 1)[-1] for c in got] == ["13"]
    assert "research grade" in got[0].evidence


@respx.mock
def test_research_grade_plant_evidence_carries_the_cal_ipc_link() -> None:
    got = search_inat({"results": [inat_observation()]})
    assert len(got) == 1
    evidence = got[0].evidence
    assert "research grade" in evidence
    assert "community identification Arundo donax" in evidence
    assert "https://www.cal-ipc.org/plants/profile/arundo-donax-profile/" in evidence
    assert got[0].author == "Sam Willow"


@respx.mock
def test_a_cc_by_photo_with_nobody_named_is_dropped() -> None:
    got = search_commons(
        commons_payload(
            commons_page("No_author.jpg", "cc-by-sa-4.0", artist=""),
            commons_page("Has_author.jpg", "cc-by-sa-4.0"),
        )
    )
    assert [c.title for c in got] == ["File:Has_author.jpg"]


@respx.mock
def test_only_photo_files_are_kept() -> None:
    got = search_commons(
        commons_payload(
            commons_page("Plan.svg", "cc0"),
            commons_page("Scan.tif", "cc0"),
            commons_page("Photo.jpg", "cc0"),
        )
    )
    assert [c.title for c in got] == ["File:Photo.jpg"]


def test_the_rate_limit_waits_a_second_between_requests() -> None:
    now = {"t": 100.0}
    slept: list[float] = []

    def clock() -> float:
        return now["t"]

    def sleeper(seconds: float) -> None:
        slept.append(seconds)
        now["t"] += seconds

    limiter = RateLimit(1.0, clock=clock, sleeper=sleeper)
    limiter.wait()  # the first request waits for nothing
    assert slept == []
    limiter.wait()  # straight away, so it has to wait a whole second
    assert slept == [1.0]
    now["t"] += 5.0
    limiter.wait()  # five seconds later, so no waiting
    assert slept == [1.0]


def test_the_rate_limit_is_used_on_every_request() -> None:
    calls: list[str] = []

    class Counting(RateLimit):
        def wait(self) -> None:
            calls.append("wait")

    with respx.mock:
        respx.get(COMMONS_API).mock(
            return_value=httpx.Response(200, json=commons_payload(commons_page("A.jpg", "cc0")))
        )
        respx.get(INAT_API).mock(return_value=httpx.Response(200, json={"results": []}))
        limiter = Counting(0.0)
        with client() as c:
            run_search(c, limiter, COMMONS_SEARCH, "artificial_bank", {}, 5)
            run_search(c, limiter, INAT_SEARCH, "invasive_plant", CAL_IPC, 5)
    assert calls == ["wait", "wait"]


def test_licence_codes_map_to_the_manifest_at_the_exact_version() -> None:
    """The allowlist takes CC BY and CC BY-SA at 2.0, 3.0 and 4.0, each recorded as given."""
    for code, expected in (
        ("cc-by-sa-4.0", "CC-BY-SA-4.0"),
        ("cc-by-sa-3.0", "CC-BY-SA-3.0"),
        ("cc-by-sa-2.0", "CC-BY-SA-2.0"),
        ("cc-by-4.0", "CC-BY-4.0"),
        ("cc-by-3.0", "CC-BY-3.0"),
        ("cc-by-2.0", "CC-BY-2.0"),
    ):
        got = licence_from_commons(code)
        assert got is not None and got.manifest == expected, code
    # A version older than 2.0 is still refused rather than rounded up to one we do allow.
    by_1 = licence_from_commons("cc-by-1.0")
    assert by_1 is not None and by_1.manifest == ""
    # Non commercial is not an open licence for our purposes, and neither is a bare "pd" tag.
    assert licence_from_commons("cc-by-nc-4.0") is None
    assert licence_from_commons("pd") is None
    assert licence_from_inat("cc0") == Licence("cc0-1.0", "CC0 1.0", "CC0-1.0", "cc0")
    assert licence_from_inat("cc-by-nc") is None
    assert licence_from_inat(None) is None


@respx.mock
def test_the_sheet_shows_what_a_person_needs_and_downloads_nothing(tmp_path: Path) -> None:
    got = search_commons(commons_payload(commons_page("Bank.jpg", "cc-by-sa-4.0")))
    html = sheet_html("artificial_bank", got, datetime(2026, 9, 20, 21, 0, tzinfo=UTC))
    assert "https://thumb.wikimedia.org/thumb/Bank.jpg/320px-Bank.jpg" in html
    assert "https://commons.wikimedia.org/wiki/File:Bank.jpg" in html
    assert "Jo Rivers" in html
    assert "CC BY-SA 4.0" in html
    assert "Concrete lined channel on a city creek" in html
    assert "fetch_open_photo.py" in html

    (tmp_path / "photos").mkdir()
    path = write_sheet("artificial_bank", got, tmp_path)
    assert path == tmp_path / "photos" / "candidates" / "artificial_bank.html"
    written = sorted(p.name for p in (tmp_path / "photos").rglob("*") if p.is_file())
    assert written == ["artificial_bank.html"], "nothing is downloaded into the repo"


@respx.mock
def test_the_sheet_lets_a_person_pick_and_build_the_picks_file() -> None:
    """Update 11 needs photos/candidates/picks-<feature>.csv, and this is where it comes from."""
    got = search_commons(commons_payload(commons_page("Bank.jpg", "cc-by-sa-4.0")))
    html = sheet_html("artificial_bank", got, datetime(2026, 9, 21, 5, 0, tzinfo=UTC))

    # One pick control per candidate fetch could actually record.
    assert html.count('class="take"') == len(got)
    assert 'class="role"' in html and 'class="scene"' in html
    # A feature sheet offers the three roles the test flow uses, with their targets.
    for role in ("test", "lesson", "practice"):
        assert f'<option value="{role}">' in html
    assert '"test": 4' in html and '"lesson": 4' in html and '"practice": 1' in html
    # It builds the file itself, in the browser, so nothing leaves the machine.
    assert "picks-' + FEATURE + '.csv" in html
    assert "url,feature,role,side,scene,notes" in html


@respx.mock
def test_the_warmup_sheet_only_offers_the_warmup_role() -> None:
    got = search_commons(commons_payload(commons_page("Creek.jpg", "cc0-1.0")))
    html = sheet_html("warmup", got, datetime(2026, 9, 21, 5, 0, tzinfo=UTC))
    assert '<option value="warmup">' in html
    for role in ("test", "lesson", "practice"):
        assert f'<option value="{role}">' not in html
    assert '"warmup": 2' in html


def test_a_candidate_fetch_would_refuse_gets_no_pick_control() -> None:
    """Picking something the tool then refuses wastes a person's evening."""
    from scripts.find_open_photos import pick_control

    refused = Candidate(
        feature="artificial_bank",
        side="present",
        source="wikimedia-commons",
        title="x",
        page_url="https://commons.wikimedia.org/wiki/File:X.jpg",
        image_url="https://x/x.jpg",
        thumb_url="https://x/t.jpg",
        author="Someone",
        licence=Licence("cc-by-1.0", "CC BY 1.0", "", "cc-by-1.0"),
        words="",
        evidence="",
        term="t",
    )
    got = search_commons(commons_payload(commons_page("Ok.jpg", "cc-by-4.0")))
    html = sheet_html("artificial_bank", [*got, refused], datetime(2026, 9, 21, 5, 0, tzinfo=UTC))
    # Every candidate gets a card, but only the ones fetch can record get a pick control.
    assert html.count('class="card"') == len(got) + 1
    assert html.count('class="take"') == len(got)
    # The helper is what the sheet relies on, so check it directly too.
    assert pick_control("artificial_bank", refused) == ""
