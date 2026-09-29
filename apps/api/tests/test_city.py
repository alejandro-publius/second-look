"""The analyst's view: findings, what a creek needs, pipes worth testing, and the pin guards.

The pure judgement is tested in core/tests/test_act.py. This checks the part that only a real
stored visit can check: that the form item a person answered reaches the right finding key, and
that every number comes back with the visit ids behind it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from apps.api import content, core_calls
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
    # Answer the dry pipe question only when it was asked: a quiet visit is asked nothing.
    asked = {f["rule_id"] for f in draft["followups"]}
    done = client.post(
        "/api/check/finalize",
        json={
            "draft_id": draft["draft_id"],
            "followup_answers": {"dry_pipe": dry_answer} if "dry_pipe" in asked else {},
            "final_rating": "good",
        },
    )
    assert done.status_code == 200, done.text
    return done.json()


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


def test_what_this_creek_needs_comes_from_approved_sentences_with_their_source(client, monkeypatch):
    """Hard rule 5, at the endpoint. Update 13 approved the city measures, so a built bank and a
    running pipe now point at OneAquaHealth's own restoration measures, each with its source and
    the visits behind it. Nothing unapproved can appear: every need is an approved sentence."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    made = a_visit(client, token=None, spot=NEW_SPOT, answers=GOOD_ANSWERS)
    view = client.get(f"/api/city/{creek_of(client, made['spot_id'])}").json()
    assert view["measures_waiting_for_approval"] is False
    ids = [n["sentence_id"] for n in view["needs"]]
    assert (
        "city_fix_sewers" in ids and "city_replant_margins" in ids and "city_remove_concrete" in ids
    )
    for need in view["needs"]:
        assert need["text"] and "Policy Brief" in need["source"]
        assert need["visit_ids"] == [made["visit_id"]] and need["fhir"]
    # Only approved sentences, and only city ones, ever reach this list.
    approved = {
        s["id"]
        for s in content.get_content().sentences
        if s.get("approved") is True and s["audience"] == "city"
    }
    assert set(ids) <= approved


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


# CRITIC_06 H01: a check that reported only a plant that does not belong made no finding at all,
# so /city said "Nobody has checked this creek yet." over one visit. The yes and the list of which
# plants are one answer about one feature, and "cant_tell" is a real answer to the list.
PLANT_ONLY = {
    **GOOD_ANSWERS,
    "bank_type": "absent",
    "draining_pipes": "absent",
    "invasive_species": "present",
    "invasive_which": ["cant_tell"],
}


def test_a_plant_is_a_finding_that_asks_the_city_for_no_measure(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    made = a_visit(client, token=None, spot=NEW_SPOT, answers=PLANT_ONLY)
    view = client.get(f"/api/city/{creek_of(client, made['spot_id'])}").json()
    assert view["visits"] == 1 and view["spots"] == 1
    (plant,) = view["findings"]
    assert plant["feature"] == "invasive_plant"
    assert plant["feature_name"] == "Plants that do not belong"
    assert plant["observers"] == 1 and plant["visit_ids"] == [made["visit_id"]]
    assert plant["fhir"] == [f"/api/fhir/Bundle/{made['visit_id']}"]
    # OneAquaHealth's four measures have none for a plant, and inventing one is not ours.
    assert view["needs"] == [] and view["measures_waiting_for_approval"] is False


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


# The referral and the way back (Update 10 tier 1 item 2) ------------------------------------------


def passing_session(client) -> str:
    """A sitting that answers every item from the gold key, so every feature is 4 of 4."""
    from apps.api import content
    from apps.api.tests.conftest import SESSION_BODY

    created = client.post("/api/test/session", json=SESSION_BODY).json()
    sid = created["session_id"]
    for position, item_id in enumerate(created["item_order"]):
        answer = "yes" if content.gold_for(item_id) == "present" else "no"
        r = client.post(
            "/api/test/response",
            json={
                "session_id": sid,
                "item_id": item_id,
                "answer": answer,
                "rt_ms": 900,
                "position": position,
            },
        )
        assert r.status_code == 200, r.text
    done = client.post(
        "/api/test/complete", json={"session_id": sid, "prior_experience": "no", "keep_score": True}
    ).json()
    assert all(s["correct"] == 4 for s in done["scores"]), done
    return done["contributor_token"]


def test_two_people_who_passed_put_a_referral_on_the_pipe_and_the_example_counts_for_nothing(
    client, monkeypatch
):
    from apps.api import fhir_store
    from core.fhir_referral import check_example_bundle, check_referral_bundle, is_example

    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    # The store folder is shared by every test in this process, so count from here.
    stored_before = set(fhir_store.stored_bundle_paths())
    first = a_visit(client, token=passing_session(client), spot=NEW_SPOT, answers=GOOD_ANSWERS)
    a_visit(
        client,
        token=passing_session(client),
        spot={"spot_id": first["spot_id"]},
        answers=GOOD_ANSWERS,
    )
    creek = creek_of(client, first["spot_id"])
    before = client.get(f"/api/city/{creek}").json()
    (pipe,) = before["pipes_worth_testing"]
    assert pipe["observers"] == 2
    assert pipe["referral"] == f"/api/fhir/referral/{first['spot_id']}"
    assert pipe["example_result"] == f"/api/fhir/referral/{first['spot_id']}/example-result"

    referral = client.get(pipe["referral"])
    assert referral.status_code == 200, referral.text
    bundle = referral.json()
    assert check_referral_bundle(bundle) == []
    (request,) = [
        e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "ServiceRequest"
    ]
    assert len(request["reasonReference"]) == 2, "one Observation per person"
    assert request["subject"]["reference"].endswith(first["spot_id"])
    assert request["authoredOn"] == "2026-09-25T15:00:00Z", "authored when it was fetched"

    example = client.get(pipe["example_result"])
    assert example.status_code == 200, example.text
    result = example.json()
    assert is_example(result) and check_example_bundle(result) == []
    assert "EXAMPLE" in json.dumps(result)

    # The example is counted by nothing: the numbers are what they were, and the store holds
    # exactly the two visits.
    after = client.get(f"/api/city/{creek}").json()
    assert after == before
    new_files = set(fhir_store.stored_bundle_paths()) - stored_before
    assert len(new_files) == 2
    assert not any("example" in p.name or "referral" in p.name for p in new_files)


def test_a_pipe_not_on_the_list_has_no_referral(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    # One person, however good, is not two.
    made = a_visit(client, token=passing_session(client), spot=NEW_SPOT, answers=GOOD_ANSWERS)
    r = client.get(f"/api/fhir/referral/{made['spot_id']}")
    assert r.status_code == 404
    # The reason, as FHIR says it: an OperationOutcome (apps/api/fhir_http.py).
    assert r.json()["resourceType"] == "OperationOutcome"
    assert r.json()["issue"][0]["code"] == "not-found"
    assert "not on the list" in r.json()["issue"][0]["details"]["text"]
    assert client.get(f"/api/fhir/referral/{made['spot_id']}/example-result").status_code == 404
    assert client.get("/api/fhir/referral/spot-nowhere").status_code == 404


# The downstream note (Update 10B tier 1 item 4) ---------------------------------------------------

# Faculty Glade, a precise pin on the South Fork through the central campus.
SOUTH_FORK_PIN = {
    "new": {
        "name": "Faculty Glade bridge",
        "latitude": 37.8716,
        "longitude": -122.256,
        "coarse": False,
    }
}
# Strawberry Creek Park, where the creek comes back into daylight, three reaches below.
PARK_PIN = {
    "new": {
        "name": "Daylighted reach in the park",
        "latitude": 37.8666,
        "longitude": -122.2885,
        "coarse": False,
    }
}
QUIET_ANSWERS = {**GOOD_ANSWERS, "bank_type": "absent", "draining_pipes": "absent"}
REACHES_IN_ORDER = [
    "south-fork-canyon",
    "south-fork-campus",
    "north-fork-campus",
    "campus-west",
    "downtown-culvert",
    "strawberry-creek-park",
    "west-culvert",
]


def test_the_slug_link_shows_the_creek_with_its_reaches_before_anyone_has_checked_it(client):
    view = client.get("/api/city/strawberry-creek").json()
    assert view["creek_slug"] == "strawberry-creek" and view["creek_name"] == "Strawberry Creek"
    assert view["visits"] == 0 and view["spots"] == 0 and view["findings"] == []
    assert [r["slug"] for r in view["reaches"]] == REACHES_IN_ORDER
    assert view["reaches"][0]["flows_into"] == "south-fork-campus"
    assert view["reaches"][0]["flows_into_name"] == "South Fork, central campus"
    assert view["reaches"][-1]["flows_into"] is None
    assert view["downstream_notes"] == []


def test_a_finding_on_a_reach_adds_one_line_to_every_reach_below_it(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    upstream = a_visit(client, token=None, spot=SOUTH_FORK_PIN, answers=GOOD_ANSWERS)
    downstream = a_visit(client, token=None, spot=PARK_PIN, answers=QUIET_ANSWERS)

    view = client.get("/api/city/strawberry-creek").json()
    assert view["visits"] == 2 and view["spots"] == 2 and view["unplaced_spots"] == 0
    by_slug = {r["slug"]: r for r in view["reaches"]}
    assert by_slug["south-fork-campus"]["spots"] == 1
    assert by_slug["strawberry-creek-park"]["spots"] == 1

    # Two findings (built banks, pipes) on the South Fork, four reaches below it: eight lines.
    notes = view["downstream_notes"]
    assert len(notes) == 8
    assert {n["from_reach_slug"] for n in notes} == {"south-fork-campus"}
    assert [n["reach_slug"] for n in notes if n["feature"] == "artificial_bank"] == [
        "campus-west",
        "downtown-culvert",
        "strawberry-creek-park",
        "west-culvert",
    ]
    bank = next(n for n in notes if n["feature"] == "artificial_bank")
    assert bank["line"] == "Upstream of here, one person reported built banks on Sep 25."
    assert bank["visit_ids"] == [upstream["visit_id"]], "every line carries its evidence"
    assert bank["fhir"] == [f"/api/fhir/Bundle/{upstream['visit_id']}"]
    # Nothing is above the South Fork's canyon reach, and nothing was reported on it.
    assert by_slug["south-fork-canyon"]["notes"] == []
    assert len(by_slug["strawberry-creek-park"]["notes"]) == 2

    # The park spot's own record carries the two lines from upstream; the upstream spot's does not.
    park = client.get(f"/api/spot/{downstream['spot_id']}").json()
    assert park["place"]["reach_slug"] == "strawberry-creek-park"
    assert sorted(n["feature"] for n in park["downstream_notes"]) == [
        "artificial_bank",
        "pipe_running",
    ]
    assert all(n["reach_slug"] == "strawberry-creek-park" for n in park["downstream_notes"])
    glade = client.get(f"/api/spot/{upstream['spot_id']}").json()
    assert glade["place"]["reach_slug"] == "south-fork-campus"
    assert glade["downstream_notes"] == []


def test_a_plant_on_a_reach_adds_a_line_below_it_and_asks_for_nothing(client, monkeypatch):
    """CRITIC_06 H01. A plant is reported like anything else, so the reaches below hear of it,
    in the same plain line that names who and when and nothing about what it means."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    made = a_visit(client, token=None, spot=SOUTH_FORK_PIN, answers=PLANT_ONLY)
    view = client.get("/api/city/strawberry-creek").json()
    notes = view["downstream_notes"]
    assert [n["reach_slug"] for n in notes] == [
        "campus-west",
        "downtown-culvert",
        "strawberry-creek-park",
        "west-culvert",
    ]
    for n in notes:
        assert n["feature"] == "invasive_plant" and n["visit_ids"] == [made["visit_id"]]
        assert (
            n["line"]
            == "Upstream of here, one person reported plants that do not belong on Sep 25."
        )
    assert view["needs"] == []


def test_the_generated_creek_id_and_the_slug_show_the_same_creek(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    made = a_visit(client, token=None, spot=SOUTH_FORK_PIN, answers=GOOD_ANSWERS)
    by_id = client.get(f"/api/city/{creek_of(client, made['spot_id'])}").json()
    by_slug = client.get("/api/city/strawberry-creek").json()
    assert by_id["creek_slug"] == "strawberry-creek"
    assert by_id["creek_name"] == by_slug["creek_name"] == "Strawberry Creek"
    assert by_id["visits"] == by_slug["visits"] == 1
    assert by_id["downstream_notes"] == by_slug["downstream_notes"]
    # A creek the pack does not know still works by its stored id, with no reaches to speak of.
    far = {
        "new": {
            "name": "Codornices Creek",
            "latitude": 37.89,
            "longitude": -122.28,
            "coarse": False,
        }
    }
    other = a_visit(client, token=None, spot=far, answers=GOOD_ANSWERS)
    view = client.get(f"/api/city/{creek_of(client, other['spot_id'])}").json()
    assert view["creek_slug"] is None and view["reaches"] == [] and view["visits"] == 1


def test_a_coarse_pin_counts_on_the_creek_but_neither_gives_nor_gets_a_note(client, monkeypatch):
    """A coarse pin is rounded to about a kilometre, so no box a few hundred metres across can
    say which reach it is on. It counts in the numbers and stays out of the notes."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    made = a_visit(client, token=None, spot=NEW_SPOT, answers=GOOD_ANSWERS)
    view = client.get("/api/city/strawberry-creek").json()
    assert view["visits"] == 1 and view["spots"] == 1
    assert view["unplaced_spots"] == 1
    assert view["downstream_notes"] == []
    assert all(r["spots"] == 0 for r in view["reaches"])
    record = client.get(f"/api/spot/{made['spot_id']}").json()
    assert record["place"] == {
        "creek_slug": "strawberry-creek",
        "creek_name": "Strawberry Creek",
        "reach_slug": None,
        "reach_name": None,
    }
    assert record["downstream_notes"] == []


# /api/creeks, and the score carried structurally in the record ------------------------------------


def test_creeks_lists_every_creek_with_its_visit_ids(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    assert client.get("/api/creeks").json() == {"creeks": []}
    glade = a_visit(client, token=None, spot=SOUTH_FORK_PIN, answers=GOOD_ANSWERS)
    far = {
        "new": {
            "name": "Codornices Creek",
            "latitude": 37.89,
            "longitude": -122.28,
            "coarse": False,
        }
    }
    other = a_visit(client, token=None, spot=far, answers=GOOD_ANSWERS)
    a_visit(
        client,
        token=None,
        spot={"new": {"name": "test spot", "latitude": 37.9, "longitude": -122.3, "coarse": False}},
        answers=GOOD_ANSWERS,
    )
    listed = client.get("/api/creeks").json()["creeks"]
    assert [c["creek"] for c in listed][0] == "strawberry-creek", "slug creeks first"
    assert len(listed) == 2, "the pin named like a test makes no creek"
    strawberry, codornices = listed
    assert strawberry["visit_ids"] == [glade["visit_id"]] and strawberry["visits"] == 1
    assert strawberry["fhir"] == [f"/api/fhir/Bundle/{glade['visit_id']}"]
    assert strawberry["record"] == "/api/city/strawberry-creek"
    assert codornices["creek_slug"] is None and codornices["name"] == "Codornices Creek"
    assert codornices["visit_ids"] == [other["visit_id"]]


def test_the_stored_record_carries_the_observer_score_structurally(client, monkeypatch):
    """An agent reading the FHIR finds k of 4 per feature in the test sitting response, not only
    in a narrative sentence."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    made = a_visit(client, token=passing_session(client), spot=SOUTH_FORK_PIN, answers=GOOD_ANSWERS)
    bundle = client.get(f"/api/fhir/Bundle/{made['visit_id']}").json()
    responses = [
        e["resource"]
        for e in bundle["entry"]
        if e["resource"]["resourceType"] == "QuestionnaireResponse"
    ]
    sittings = [r for r in responses if r["id"].startswith("sl-qr-test-")]
    assert len(sittings) == 1
    scores = {i["linkId"]: i["item"][0]["answer"][0]["valueInteger"] for i in sittings[0]["item"]}
    assert scores == {
        "artificial_bank": 4,
        "dug_out_channel": 4,
        "invasive_plant": 4,
        "pipe_running": 4,
    }
    assert (
        "sitting-" in sittings[0]["identifier"]["value"]
        and len(sittings[0]["identifier"]["value"]) < 30
    )
    # An anonymous visit carries no sitting at all.
    quiet = a_visit(client, token=None, spot=PARK_PIN, answers=QUIET_ANSWERS)
    anon = client.get(f"/api/fhir/Bundle/{quiet['visit_id']}").json()
    assert not any(e["resource"].get("id", "").startswith("sl-qr-test-") for e in anon["entry"])
