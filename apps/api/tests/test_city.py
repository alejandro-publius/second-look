"""The analyst's view: findings, what a creek needs, pipes worth testing, and the pin guards.

The pure judgement is tested in core/tests/test_act.py. This checks the part that only a real
stored visit can check: that the form item a person answered reaches the right finding key, and
that every number comes back with the visit ids behind it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.api import core_calls
from apps.api.tests.conftest import freeze_now, full_session
from apps.api.tests.test_check import GOOD_ANSWERS, NEW_SPOT, _dry

NOW = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)


def creek_of(client, spot_id: str) -> str:
    """A creek id is made when the first spot on it is made, so read it back rather than guess."""
    return client.get(f"/api/spot/{spot_id}").json()["spot"]["creek_id"]


def a_visit(client, *, token: str | None, spot: dict, answers: dict, dry_answer: str = "yes"):
    body = {"spot": spot, "answers": answers, "first_rating": "good", "photo_ids": []}
    if token:
        body["contributor_token"] = token
    draft = client.post("/api/check/draft", json=body).json()
    return client.post(
        "/api/check/finalize",
        json={
            "draft_id": draft["draft_id"],
            "followup_answers": {"dry_pipe": dry_answer},
            "final_rating": "good",
        },
    ).json()


def test_an_unknown_creek_is_404(client):
    assert client.get("/api/city/nowhere").status_code == 404


def test_a_finding_carries_the_visits_behind_it_and_counts_people_not_visits(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    token = full_session(client, keep_score=True, answer="yes")["contributor_token"]
    first = a_visit(client, token=token, spot=NEW_SPOT, answers=GOOD_ANSWERS)
    # The same person again at the same spot. One person, two visits.
    a_visit(
        client,
        token=token,
        spot={"spot_id": first["spot_id"]},
        answers=GOOD_ANSWERS,
    )

    creek = creek_of(client, first["spot_id"])
    view = client.get(f"/api/city/{creek}").json()
    assert view["creek_id"] == creek
    assert view["visits"] == 2 and view["spots"] == 1

    by_feature = {f["feature"]: f for f in view["findings"]}
    # bank_type on the form is artificial_bank the feature: the mapping really is applied.
    assert "artificial_bank" in by_feature, view["findings"]
    bank = by_feature["artificial_bank"]
    assert bank["observers"] == 1, "one person, however often they visit"
    assert len(bank["visit_ids"]) == 2
    assert bank["fhir"] == [f"/api/fhir/Bundle/{v}" for v in bank["visit_ids"]]
    assert bank["feature_name"] == "Built banks"


def test_no_measure_is_shown_while_no_sentence_is_approved(client, monkeypatch):
    """Hard rule 5, at the endpoint. A city sees nothing rather than words nobody checked."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    made = a_visit(client, token=None, spot=NEW_SPOT, answers=GOOD_ANSWERS)
    view = client.get(f"/api/city/{creek_of(client, made['spot_id'])}").json()
    assert view["needs"] == []
    assert view["measures_waiting_for_approval"] is True


def test_a_pipe_needs_two_people_who_both_passed(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    # full_session answers yes to everything, which is 2 of 4 per feature: below the pass mark.
    weak = full_session(client, keep_score=True, answer="yes")["contributor_token"]
    first = a_visit(client, token=weak, spot=NEW_SPOT, answers=GOOD_ANSWERS)
    creek = creek_of(client, first["spot_id"])
    view = client.get(f"/api/city/{creek}").json()
    assert view["pipes_worth_testing"] == [], "one person, and they did not pass"

    # A second person, also below the pass mark, still does not put the pipe on the list.
    weak2 = full_session(client, keep_score=True, answer="yes")["contributor_token"]
    a_visit(client, token=weak2, spot={"spot_id": first["spot_id"]}, answers=GOOD_ANSWERS)
    after = client.get(f"/api/city/{creek}").json()
    assert after["pipes_worth_testing"] == [], "two people, neither of whom passed"
    # The finding is still recorded: not being trusted with a sample bottle is not being ignored.
    assert any(f["feature"] == "pipe_running" for f in after["findings"])


def test_a_pin_that_reads_like_a_test_is_flagged_and_left_out_of_the_numbers(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    # Far enough away to be its own spot, and named like somebody trying the form out.
    pin = {"new": {"name": "test spot", "latitude": 37.9, "longitude": -122.3, "coarse": False}}
    made = a_visit(client, token=None, spot=pin, answers=GOOD_ANSWERS)
    view = client.get(f"/api/city/{creek_of(client, made['spot_id'])}").json()

    # Counted nowhere.
    assert view["spots"] == 0 and view["visits"] == 0
    assert view["findings"] == [] and view["pipes_worth_testing"] == []
    # Listed for a person to look at.
    assert [s["spot_name"] for s in view["flagged_spots"]] == ["test spot"]
    assert view["flagged_spots"][0]["why"] == "the name reads like a test"
    # And still there, because deleting somebody's visit is not ours to do.
    assert client.get(f"/api/spot/{made['spot_id']}").status_code == 200


def test_a_pin_within_thirty_metres_offers_the_spot_that_is_already_there(client, monkeypatch):
    """Update 10 tier 1 item 3. A suggestion, never a merge: two spots 25 metres apart can be
    two real places, and quietly folding one into the other loses a visit nobody gets back."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    # Both pins precise: a coarse pin is rounded to about a kilometre and cannot be compared.
    precise = {
        "new": {
            "name": "Strawberry Creek at the footbridge",
            "latitude": 37.87312,
            "longitude": -122.26041,
            "coarse": False,
        }
    }
    first = a_visit(client, token=None, spot=precise, answers=GOOD_ANSWERS)

    nearly = {
        "new": {
            "name": "Strawberry Creek, the same footbridge",
            "latitude": 37.8731,
            "longitude": -122.2604,
            "coarse": False,
        }
    }
    draft = client.post(
        "/api/check/draft",
        json={"spot": nearly, "answers": GOOD_ANSWERS, "first_rating": "good", "photo_ids": []},
    ).json()
    near = draft["nearby_spot"]
    assert near is not None, "an existing spot a few metres away must be offered"
    assert near["spot_id"] == first["spot_id"]
    assert near["metres"] <= 30

    # A pin a long way off is a new place and is not offered anything.
    far = {
        "new": {
            "name": "Codornices Creek",
            "latitude": 37.89,
            "longitude": -122.28,
            "coarse": False,
        }
    }
    far_draft = client.post(
        "/api/check/draft",
        json={"spot": far, "answers": GOOD_ANSWERS, "first_rating": "good", "photo_ids": []},
    ).json()
    assert far_draft["nearby_spot"] is None


def test_a_coarse_pin_is_never_offered_a_neighbour(client, monkeypatch):
    """Its position is rounded to about a kilometre, so thirty metres means nothing."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    precise = {
        "new": {
            "name": "Strawberry Creek at the footbridge",
            "latitude": 37.87312,
            "longitude": -122.26041,
            "coarse": False,
        }
    }
    a_visit(client, token=None, spot=precise, answers=GOOD_ANSWERS)
    coarse = {
        "new": {
            "name": "Somewhere near the footbridge",
            "latitude": 37.87312,
            "longitude": -122.26041,
            "coarse": True,
        }
    }
    draft = client.post(
        "/api/check/draft",
        json={"spot": coarse, "answers": GOOD_ANSWERS, "first_rating": "good", "photo_ids": []},
    ).json()
    assert draft["nearby_spot"] is None
