"""Creek check: draft, follow-ups, finalize, the spot view, quick checks.

Rainfall is faked at apps.api.core_calls.rain_status so nothing touches the network. Everything
else runs the real core modules and the real FHIR store into a temp folder."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from apps.api import core_calls
from apps.api.db import engine
from apps.api.models import CheckResultRow, SpotRow, VisitRow
from apps.api.tests.conftest import freeze_now, full_session

NOW = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)
NEW_SPOT = {
    "new": {
        "name": "Strawberry Creek at the footbridge",
        "latitude": 37.87312,
        "longitude": -122.26041,
        "coarse": True,
    }
}
GOOD_ANSWERS = {
    "channel_form": "u_shape",
    "bank_type": "present",
    "draining_pipes": "present",
    "water_flow": "slow",
    "habitats": ["riffles", "sand_banks"],
    "water_height_m": 0.3,
    "invasive_species": "absent",
    "feelings": ["joy:4", "fear:not_applicable"],
    "overall_rating": "good",
}


def must(value):
    assert value is not None
    return value


def _dry(*_a, **_k):
    return core_calls.RainView(status="dry", mm_in_window=0.0, dry_days=5, source="open-meteo")


def _unknown(*_a, **_k):
    return core_calls.RainView()


def _draft(client, **extra):
    body = {"spot": NEW_SPOT, "answers": GOOD_ANSWERS, "first_rating": "good", "photo_ids": []}
    body.update(extra)
    return client.post("/api/check/draft", json=body)


def test_draft_asks_the_dry_pipe_and_rating_check_questions(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    r = _draft(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"draft_id", "followups", "nearby_spot"}
    assert body["nearby_spot"] is None, "the first pin on an empty map has no neighbour"
    rules = [f["rule_id"] for f in body["followups"]]
    assert rules == ["dry_pipe", "rating_check"]
    dry, rating = body["followups"]
    assert dry["kind"] == "yesno" and "5 days" in dry["question_text"]
    assert rating["kind"] == "keep_rating" and "artificial banks" in rating["question_text"]
    assert "{" not in dry["question_text"] + rating["question_text"]
    with Session(engine) as db:
        spot = db.exec(select(SpotRow)).one()
        visit = must(db.get(VisitRow, body["draft_id"]))
    assert (spot.latitude, spot.longitude) == (37.87, -122.26)  # coarse: about 1 km
    assert visit.finalized_at is None and visit.first_rating == "good"
    assert json.loads(visit.site_json)["status"] == "dry"


def test_unknown_rain_skips_the_dry_pipe_question(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)
    rules = [f["rule_id"] for f in _draft(client).json()["followups"]]
    assert "dry_pipe" not in rules


def test_followup_selection_is_the_core_function_and_feature_names_come_from_content(
    client, monkeypatch
):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)
    seen: dict[str, Any] = {}

    def fake_select(answers, rain, observer, *, table, form_items, checker_enabled):
        seen.update(answers=dict(answers), rain=rain.status, checker=checker_enabled)
        return [
            core_calls.FollowupView(
                rule_id="low_score",
                kind="photo",
                question_key="followup.low_score",
                params={"correct": 1, "feature": "pipe running"},
            ),
            core_calls.FollowupView(
                rule_id="checker_flag",
                kind="look_again",
                question_key="followup.checker_flag",
                params={"note": "a built edge"},
            ),
        ]

    monkeypatch.setattr(core_calls, "select_followups", fake_select)
    body = _draft(client).json()
    assert seen["answers"]["bank_type"] == "present" and seen["rain"] == "unknown"
    assert seen["checker"] is False
    low, flag = body["followups"]
    assert low["kind"] == "photo"
    assert "1 of 4 on Pipes and sewage signs" in low["question_text"]
    assert flag["kind"] == "yesno" and "a built edge" in flag["question_text"]


def test_draft_refuses_free_text_and_unknown_items(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)
    bad = [
        {"channel_form": "my own words"},
        {"not_an_item": "present"},
        {"invasive_which": ["a plant I made up"]},
        {"water_height_m": 5000},
        {"feelings": ["joy:11"]},
        {"habitats": "riffles"},
    ]
    for answers in bad:
        r = _draft(client, answers=answers)
        assert r.status_code == 422, (answers, r.text)
        assert "detail" in r.json()
    assert _draft(client, first_rating="amazing").status_code == 422
    assert _draft(client, photo_ids=["up-missing"]).status_code == 422
    assert _draft(client, contributor_token="nosuchtoken1").status_code == 404
    with Session(engine) as db:
        assert db.exec(select(func.count()).select_from(VisitRow)).one() == 0


def test_finalize_stores_checks_builds_the_record_and_saves_fhir(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    draft = _draft(client).json()
    r = client.post(
        "/api/check/finalize",
        json={
            "draft_id": draft["draft_id"],
            "followup_answers": {"dry_pipe": "yes", "rating_check": "change"},
            "final_rating": "moderate",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["visit_id"] == draft["draft_id"]
    assert body["fhir_saved"] is True
    with Session(engine) as db:
        visit = must(db.get(VisitRow, body["visit_id"]))
        checks = db.exec(
            select(CheckResultRow).where(CheckResultRow.visit_id == body["visit_id"])
        ).all()
    assert visit.finalized_at is not None
    assert (visit.first_rating, visit.final_rating) == ("good", "moderate")
    assert {(c.rule_id, c.answer, c.asked) for c in checks} == {
        ("dry_pipe", "yes", True),
        ("rating_check", "change", True),
    }
    assert json.loads(checks[0].detail_json)["kind"] in ("yesno", "keep_rating")
    # Finalize again: same ids, nothing duplicated.
    again = client.post(
        "/api/check/finalize", json={"draft_id": draft["draft_id"], "final_rating": "poor"}
    ).json()
    assert again["visit_id"] == body["visit_id"]
    with Session(engine) as db:
        assert db.exec(select(func.count()).select_from(CheckResultRow)).one() == 2
        assert must(db.get(VisitRow, body["visit_id"])).final_rating == "moderate"


def test_finalize_refuses_answers_to_questions_that_were_not_asked(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)
    draft = _draft(client).json()
    r = client.post(
        "/api/check/finalize",
        json={"draft_id": draft["draft_id"], "followup_answers": {"dry_pipe": "yes"}},
    )
    assert r.status_code == 422
    r = client.post(
        "/api/check/finalize",
        json={"draft_id": draft["draft_id"], "followup_answers": {"rating_check": "my own words"}},
    )
    assert r.status_code == 422
    assert client.post("/api/check/finalize", json={"draft_id": "visit-none"}).status_code == 404


def test_finalize_without_the_record_builder_is_a_plain_503(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)

    def missing(**_):
        raise core_calls.RecordBuilderMissing("core.gate is not installed")

    monkeypatch.setattr(core_calls, "build_record", missing)
    draft = _draft(client).json()
    r = client.post("/api/check/finalize", json={"draft_id": draft["draft_id"]})
    assert r.status_code == 503
    assert "record builder" in r.json()["detail"]
    with Session(engine) as db:
        assert must(db.get(VisitRow, draft["draft_id"])).finalized_at is None


def test_finalize_survives_a_missing_fhir_store(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)
    monkeypatch.setattr(core_calls, "save_visit_bundle", lambda visit, **_kw: None)
    draft = _draft(client).json()
    body = client.post("/api/check/finalize", json={"draft_id": draft["draft_id"]}).json()
    assert body["fhir_saved"] is False
    with Session(engine) as db:
        assert must(db.get(VisitRow, draft["draft_id"])).finalized_at is not None


def test_spot_view_shows_answers_beside_the_observer_label(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    token = full_session(client, keep_score=True, answer="yes")["contributor_token"]  # 2 of 4 each
    draft = _draft(client, contributor_token=token).json()
    client.post(
        "/api/check/finalize",
        json={
            "draft_id": draft["draft_id"],
            "followup_answers": {"dry_pipe": "no"},
            "final_rating": "good",
        },
    )
    spot_id = client.post("/api/check/finalize", json={"draft_id": draft["draft_id"]}).json()[
        "spot_id"
    ]
    view = client.get(f"/api/spot/{spot_id}").json()
    assert set(view) == {"spot", "visits", "health_card", "place", "downstream_notes"}
    assert view["spot"]["spot_id"] == spot_id and view["spot"]["coarse"] is True
    # A coarse pin near the campus sits on Strawberry Creek, on no reach, and gets no note.
    assert view["place"]["creek_slug"] == "strawberry-creek"
    assert view["place"]["reach_slug"] is None
    assert view["downstream_notes"] == []
    assert view["health_card"] is None  # no approved sentence yet, so nothing is shown
    assert len(view["visits"]) == 1
    visit = view["visits"][0]
    assert set(visit) >= {
        "visit_id",
        "answered_at",
        "answers",
        "checks",
        "first_rating",
        "final_rating",
    }
    assert visit["answered_at"] == "2026-09-25T15:00:00Z"
    by_item = {a["item_id"]: a for a in visit["answers"]}
    bank = by_item["bank_type"]
    assert bank["feature"] == "artificial_bank"
    assert bank["label"] == "Artificial (concrete or stones with concrete)"
    assert bank["observer_label"] == "2 of 4 on Built banks, tested Sep 25"
    assert bank["observer_passed"] is False
    assert by_item["habitats"]["label"] == "Riffles, rapids, falls, Sand banks"
    assert by_item["invasive_species"]["label"] == "No"
    assert (
        by_item["channel_form"]["observer_label"] is None
        and by_item["channel_form"]["feature"] is None
    )
    assert visit["checks"][0]["rule_id"] == "dry_pipe" and visit["checks"][0]["answer"] == "no"
    assert token not in json.dumps(view)


def test_spot_view_after_ninety_days_shows_the_expired_sentence(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)
    freeze_now(NOW)
    token = full_session(client, keep_score=True)["contributor_token"]
    draft = _draft(client, contributor_token=token).json()
    spot_id = client.post("/api/check/finalize", json={"draft_id": draft["draft_id"]}).json()[
        "spot_id"
    ]
    freeze_now(NOW + timedelta(days=91))
    view = client.get(f"/api/spot/{spot_id}").json()
    bank = next(a for a in view["visits"][0]["answers"] if a["item_id"] == "bank_type")
    assert bank["observer_label"].startswith("Score expired.")
    assert bank["observer_passed"] is None


def test_anonymous_visit_has_no_label(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)
    draft = _draft(client).json()
    spot_id = client.post("/api/check/finalize", json={"draft_id": draft["draft_id"]}).json()[
        "spot_id"
    ]
    view = client.get(f"/api/spot/{spot_id}").json()
    assert all(a["observer_label"] is None for a in view["visits"][0]["answers"])
    assert view["visits"][0]["observer_scored"] is False
    assert client.get("/api/spot/spot-none").status_code == 404


def test_quick_check_joins_the_timeline_and_rejects_free_text(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _unknown)
    freeze_now(NOW)
    draft = _draft(client).json()
    spot_id = client.post("/api/check/finalize", json={"draft_id": draft["draft_id"]}).json()[
        "spot_id"
    ]
    freeze_now(NOW + timedelta(days=2))
    r = client.post(
        f"/api/quick/{spot_id}",
        json={"colour": "muddy", "smell": "none", "pipe_running": "present"},
    )
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"visit_id", "spot_id"}
    bad = client.post(
        f"/api/quick/{spot_id}",
        json={"colour": "sort of brown", "smell": "none", "pipe_running": "present"},
    )
    assert bad.status_code == 422
    assert (
        client.post(
            "/api/quick/spot-none",
            json={"colour": "clear", "smell": "none", "pipe_running": "absent"},
        ).status_code
        == 404
    )
    view = client.get(f"/api/spot/{spot_id}").json()
    assert [v["kind"] for v in view["visits"]] == ["quick", "check"]  # newest first
    quick = view["visits"][0]
    pipe = next(a for a in quick["answers"] if a["item_id"] == "pipe_running")
    assert pipe["feature"] == "pipe_running" and pipe["label"] == "present"
    assert quick["checks"] == []
