"""Sessions, assignment, answers, completion, counts, export, demo, content hash, data lock."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from apps.api import study
from apps.api.db import engine
from apps.api.models import ItemResponse, ObserverRow, RandomizationCounter, StudySession
from apps.api.tests.conftest import SESSION_BODY, freeze_now, full_session
from core.allocator import replay
from core.lock import DATA_LOCK_UTC

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)


def visitor(n: int) -> dict:
    """A session body from a browser of its own: one browser keeps one arm, so a test that
    wants twelve randomized visitors needs twelve tokens."""
    return dict(SESSION_BODY, client_token_hash=f"{n:064x}")


def must(value):
    assert value is not None
    return value


def _count(model) -> int:
    with Session(engine) as db:
        return int(db.exec(select(func.count()).select_from(model)).one())


# Sessions ---------------------------------------------------------------------------------------


def test_session_is_created_with_the_contract_shape(client):
    r = client.post("/api/test/session", json=SESSION_BODY)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"session_id", "arm", "item_order", "lesson_first"}
    assert body["arm"] in ("untrained", "trained")
    assert body["lesson_first"] is (body["arm"] == "trained")
    assert sorted(body["item_order"]) == [f"t{n:02d}" for n in range(1, 17)]


def test_item_order_differs_between_sessions(client):
    orders = {
        tuple(client.post("/api/test/session", json=SESSION_BODY).json()["item_order"])
        for _ in range(6)
    }
    assert len(orders) > 1


def test_source_label_is_coerced_and_token_is_hashed(client):
    body = dict(SESSION_BODY, source_label="https://evil.example/?x=1", ua_class="fridge")
    sid = client.post("/api/test/session", json=body).json()["session_id"]
    with Session(engine) as db:
        row = db.get(StudySession, sid)
    assert row is not None
    assert row.source_label == "other"
    assert row.ua_class == "other"
    assert row.client_token_hash != SESSION_BODY["client_token_hash"]
    assert len(row.client_token_hash) == 32
    assert row.warmup_choice == "w01"
    assert row.is_test is False


def test_unknown_warmup_choice_is_dropped_not_stored(client):
    sid = client.post("/api/test/session", json=dict(SESSION_BODY, warmup_choice="zzz")).json()[
        "session_id"
    ]
    with Session(engine) as db:
        assert must(db.get(StudySession, sid)).warmup_choice is None


def test_qa_key_header_marks_a_test_session(client):
    sid = client.post(
        "/api/test/session", json=SESSION_BODY, headers={"X-QA-Key": "test-qa-key-1234567890abcd"}
    ).json()["session_id"]
    wrong = client.post(
        "/api/test/session", json=SESSION_BODY, headers={"X-QA-Key": "nope"}
    ).json()["session_id"]
    with Session(engine) as db:
        assert must(db.get(StudySession, sid)).is_test is True
        assert must(db.get(StudySession, wrong)).is_test is False


def test_hidden_field_marks_the_session_but_the_response_is_identical(client):
    clean = client.post("/api/test/session", json=SESSION_BODY)
    trapped = client.post("/api/test/session", json=dict(SESSION_BODY, hidden_field="I am a bot"))
    assert clean.status_code == trapped.status_code == 200
    assert set(clean.json()) == set(trapped.json())
    assert clean.headers.get("content-type") == trapped.headers.get("content-type")
    with Session(engine) as db:
        assert must(db.get(StudySession, clean.json()["session_id"])).hidden_field_filled is False
        assert must(db.get(StudySession, trapped.json()["session_id"])).hidden_field_filled is True


# Assignment -------------------------------------------------------------------------------------


def test_assignment_follows_the_stored_seed_in_blocks_of_four(client):
    arms = [client.post("/api/test/session", json=visitor(i)).json()["arm"] for i in range(12)]
    with Session(engine) as db:
        counter = must(db.get(RandomizationCounter, 1))
        rows = db.exec(select(StudySession)).all()
    assert counter.next_position == 12
    assert arms == replay(counter.seed, 12)
    assert Counter(arms) == {"untrained": 6, "trained": 6}
    for block_id in range(3):
        block = [r.arm for r in rows if r.block_id == block_id]
        assert Counter(block) == {"untrained": 2, "trained": 2}


def test_take_position_never_hands_out_the_same_slot_twice_under_threads(client):
    def take(_: int) -> int:
        with Session(engine) as db:
            position, _seed = study.take_position(db)
            db.commit()
            return position

    with ThreadPoolExecutor(max_workers=16) as pool:
        positions = list(pool.map(take, range(48)))
    assert sorted(positions) == list(range(48))


def test_simultaneous_sessions_keep_every_complete_block_balanced(client):
    def create(n: int) -> str:
        r = client.post("/api/test/session", json=visitor(n))
        assert r.status_code == 200, r.text
        return r.json()["session_id"]

    with ThreadPoolExecutor(max_workers=12) as pool:
        ids = list(pool.map(create, range(40)))
    assert len(set(ids)) == 40
    with Session(engine) as db:
        rows = db.exec(select(StudySession)).all()
        counter = must(db.get(RandomizationCounter, 1))
    assert counter.next_position == 40
    per_block = Counter(r.block_id for r in rows)
    assert all(n == 4 for n in per_block.values()), per_block
    for block_id in per_block:
        block = Counter(r.arm for r in rows if r.block_id == block_id)
        assert block == {"untrained": 2, "trained": 2}, (block_id, block)


# Responses --------------------------------------------------------------------------------------


def _response(client, sid: str, item: str, answer: str, position: int = 0):
    return client.post(
        "/api/test/response",
        json={
            "session_id": sid,
            "item_id": item,
            "answer": answer,
            "rt_ms": 800,
            "position": position,
        },
    )


def test_response_is_idempotent_and_keeps_the_first_answer(client):
    sid = client.post("/api/test/session", json=SESSION_BODY).json()["session_id"]
    assert _response(client, sid, "t01", "yes").json() == {"ok": True}
    assert _response(client, sid, "t01", "yes").status_code == 200
    conflict = _response(client, sid, "t01", "no")
    assert conflict.status_code == 409
    assert "first answer stays" in conflict.json()["detail"]
    with Session(engine) as db:
        assert must(db.get(ItemResponse, (sid, "t01"))).answer == "yes"
    assert _count(ItemResponse) == 1


def test_response_body_never_reveals_correctness(client):
    sid = client.post("/api/test/session", json=SESSION_BODY).json()["session_id"]
    body = _response(client, sid, "t01", "yes").json()
    assert body == {"ok": True}


def test_response_for_unknown_session_or_item_is_404(client):
    assert _response(client, "nope", "t01", "yes").status_code == 404
    sid = client.post("/api/test/session", json=SESSION_BODY).json()["session_id"]
    assert _response(client, sid, "t99", "yes").status_code == 404
    bad = client.post(
        "/api/test/response",
        json={"session_id": sid, "item_id": "t01", "answer": "maybe", "rt_ms": 1, "position": 0},
    )
    assert bad.status_code == 422


def test_lesson_done_stores_seconds(client):
    sid = client.post("/api/test/session", json=SESSION_BODY).json()["session_id"]
    r = client.post(
        "/api/test/lesson-done",
        json={"session_id": sid, "lesson_seconds": {"artificial_bank": 12.34, "pipe_running": 8}},
    )
    assert r.json() == {"ok": True}
    with Session(engine) as db:
        assert json.loads(must(must(db.get(StudySession, sid)).lesson_seconds)) == {
            "artificial_bank": 12.3,
            "pipe_running": 8.0,
        }


# Completion -------------------------------------------------------------------------------------


def test_complete_scores_from_the_gold_key(client):
    freeze_now(NOW)
    done = full_session(client, answer="yes")
    assert set(done["scores"][0]) == {"feature", "correct", "total"}
    assert [s["feature"] for s in done["scores"]] == [
        "artificial_bank",
        "dug_out_channel",
        "invasive_plant",
        "pipe_running",
    ]
    assert all(s["correct"] == 2 and s["total"] == 4 for s in done["scores"])
    assert done["correct_total"] == 8
    assert "contributor_token" not in done
    with Session(engine) as db:
        assert must(db.get(StudySession, done["session_id"])).completed_at is not None
        assert must(db.get(StudySession, done["session_id"])).prior_experience == "no"


def test_keep_score_issues_a_token_stored_apart_from_the_session(client):
    freeze_now(NOW)
    done = full_session(client, keep_score=True, answer="cant_tell")
    token = done["contributor_token"]
    assert len(token) == 16
    with Session(engine) as db:
        row = must(db.get(ObserverRow, token))
        assert row.tested_on == NOW.date()
        assert json.loads(row.scores_json) == done["scores"]
        assert all(s["correct"] == 0 for s in json.loads(row.scores_json))
        session_row = must(db.get(StudySession, done["session_id"]))
    # No column on the session row holds the token, and no column on the observer row holds the id.
    assert token not in json.dumps(session_row.model_dump(mode="json"))
    assert done["session_id"] not in json.dumps(row.model_dump(mode="json"))


def test_partial_sitting_counts_missing_as_wrong(client):
    sid = client.post("/api/test/session", json=SESSION_BODY).json()["session_id"]
    _response(client, sid, "t01", "yes")  # t01 is present, so correct
    done = client.post("/api/test/complete", json={"session_id": sid, "keep_score": False}).json()
    assert done["correct_total"] == 1


def test_complete_twice_keeps_the_first_completion_time(client):
    freeze_now(NOW)
    done = full_session(client)
    freeze_now(NOW + timedelta(minutes=5))
    again = client.post("/api/test/complete", json={"session_id": done["session_id"]}).json()
    assert again["correct_total"] == done["correct_total"]
    with Session(engine) as db:
        completed = must(must(db.get(StudySession, done["session_id"])).completed_at)
    assert completed.replace(tzinfo=UTC) == NOW


# Counts -----------------------------------------------------------------------------------------


def test_counts_return_counts_only(client):
    # A day before the lock, whatever today is: on the real clock these sittings count as post
    # lock from 2026-09-28 on, and the last line failed (found when the lock job ran, Sep 28).
    freeze_now(NOW)
    full_session(client)
    client.post("/api/test/session", json=dict(SESSION_BODY, source_label="chat"))
    client.post(
        "/api/test/session", json=SESSION_BODY, headers={"X-QA-Key": "test-qa-key-1234567890abcd"}
    )
    body = client.get("/api/test/counts").json()
    assert set(body) == {"by_arm", "by_source", "post_lock"}
    assert set(body["by_arm"]) == {"untrained", "trained"}
    assert set(body["by_arm"]["trained"]) == {"randomized", "completed"}
    assert sum(a["randomized"] for a in body["by_arm"].values()) == 2  # QA session left out
    assert sum(a["completed"] for a in body["by_arm"].values()) == 1
    # "panel" joined the labels on 2026-09-24 (docs/deviations.md, the panel study).
    assert body["by_source"] == {
        "poster": 1,
        "chat": 0,
        "friends": 0,
        "creek_group": 0,
        "other": 0,
        "panel": 0,
    }
    assert body["post_lock"] == 0


# Export -----------------------------------------------------------------------------------------


def _read_zip(data: bytes) -> dict[str, list[dict[str, str]]]:
    out = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            out[name] = list(csv.DictReader(io.StringIO(zf.read(name).decode())))
    return out


def test_export_needs_the_token_and_returns_the_exact_schema(client):
    assert client.get("/api/test/export").status_code == 404
    assert client.get("/api/test/export?token=wrong").status_code == 404
    freeze_now(NOW)
    done = full_session(client, answer="no")
    r = client.get("/api/test/export?token=test-export-token-1234567890")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    files = _read_zip(r.content)
    assert set(files) == {"sessions.csv", "responses.csv"}
    assert list(files["sessions.csv"][0]) == study.SESSIONS_COLUMNS
    assert list(files["responses.csv"][0]) == study.RESPONSES_COLUMNS
    s = files["sessions.csv"][0]
    assert s["session_id"] == done["session_id"]
    assert s["started_at_utc"] == "2026-09-23T12:00:00Z"
    assert s["completed_at_utc"] == "2026-09-23T12:00:00Z"
    assert s["test_seconds"] == "0.0"
    assert (s["is_test"], s["post_lock"], s["hidden_field_filled"]) == ("0", "0", "0")
    assert s["prior_experience"] == "no" and s["warmup_choice"] == "w01"
    rows = files["responses.csv"]
    assert len(rows) == 16
    by_item = {r["item_id"]: r for r in rows}
    assert by_item["t01"]["gold"] == "present" and by_item["t01"]["correct"] == "0"
    assert by_item["t03"]["gold"] == "absent" and by_item["t03"]["correct"] == "1"
    assert by_item["t05"]["feature"] == "dug_out_channel"
    assert all(r["answer"] == "no" for r in rows)


def test_export_holds_no_identifier_columns(client):
    full_session(client)
    files = _read_zip(client.get("/api/test/export?token=test-export-token-1234567890").content)
    for name, rows in files.items():
        for column in rows[0]:
            assert not any(word in column for word in ("ip", "email", "name", "address")), (
                name,
                column,
            )


# Resume and the gap at complete (Update 07 sections 1.2, 1.3 and 2.1) --------------------------


def test_resume_returns_the_same_arm_the_same_order_and_what_we_hold(client):
    created = client.post("/api/test/session", json=SESSION_BODY).json()
    sid = created["session_id"]
    for position, item_id in enumerate(created["item_order"][:7]):
        assert _response(client, sid, item_id, "yes", position).status_code == 200
    state = client.get("/api/test/resume", params={"session_id": sid}).json()
    assert state["arm"] == created["arm"]
    assert state["item_order"] == created["item_order"]
    assert state["lesson_first"] == created["lesson_first"]
    assert state["answered"] == created["item_order"][:7]
    assert state["completed"] is False
    # The next unanswered item is item 8, which is where a reload picks the sitting back up.
    nxt = [i for i in state["item_order"] if i not in state["answered"]][0]
    assert nxt == created["item_order"][7]


def test_resume_creates_no_session_row_and_mints_no_token(client):
    freeze_now(NOW)
    done = full_session(client, keep_score=True)
    sessions_before = _count(StudySession)
    tokens_before = _count(ObserverRow)
    state = client.get("/api/test/resume", params={"session_id": done["session_id"]}).json()
    assert state["completed"] is True
    assert state["correct_total"] == done["correct_total"]
    assert state["scores"] == done["scores"]
    assert "contributor_token" not in state
    assert _count(StudySession) == sessions_before
    assert _count(ObserverRow) == tokens_before


def test_resume_of_an_unknown_session_is_404(client):
    assert client.get("/api/test/resume", params={"session_id": "nope"}).status_code == 404


def test_resume_during_the_lesson_keeps_the_trained_arm(client):
    created = client.post("/api/test/session", json=SESSION_BODY).json()
    sid = created["session_id"]
    state = client.get("/api/test/resume", params={"session_id": sid}).json()
    assert state["lesson_done"] is False
    client.post("/api/test/lesson-done", json={"session_id": sid, "lesson_seconds": {"a": 1.0}})
    after = client.get("/api/test/resume", params={"session_id": sid}).json()
    assert after["lesson_done"] is True
    assert after["arm"] == created["arm"]
    assert after["item_order"] == created["item_order"]


def test_complete_names_the_answers_it_does_not_hold_and_scores_nothing_yet(client):
    created = client.post("/api/test/session", json=SESSION_BODY).json()
    sid = created["session_id"]
    for position, item_id in enumerate(created["item_order"][:15]):
        assert _response(client, sid, item_id, "yes", position).status_code == 200
    missed = created["item_order"][15]
    first = client.post(
        "/api/test/complete", json={"session_id": sid, "keep_score": False, "answered_count": 16}
    ).json()
    assert first["need_resend"] == [missed]
    assert first["stored_count"] == 15
    assert "scores" not in first
    with Session(engine) as db:
        assert must(db.get(StudySession, sid)).completed_at is None
    # The browser sends the one we are missing from its own copy, then asks again.
    assert _response(client, sid, missed, "yes", 15).status_code == 200
    second = client.post(
        "/api/test/complete", json={"session_id": sid, "keep_score": False, "answered_count": 16}
    ).json()
    assert second["correct_total"] == 8
    with Session(engine) as db:
        assert must(db.get(StudySession, sid)).unsent_count == 0


def test_a_gap_that_cannot_be_closed_is_recorded_as_unsent(client):
    created = client.post("/api/test/session", json=SESSION_BODY).json()
    sid = created["session_id"]
    for position, item_id in enumerate(created["item_order"][:14]):
        assert _response(client, sid, item_id, "yes", position).status_code == 200
    done = client.post(
        "/api/test/complete",
        json={"session_id": sid, "keep_score": False, "answered_count": 16, "final": True},
    ).json()
    assert "need_resend" not in done
    with Session(engine) as db:
        assert must(db.get(StudySession, sid)).unsent_count == 2


def test_a_browser_that_answered_everything_is_never_asked_to_resend(client):
    freeze_now(NOW)
    created = client.post("/api/test/session", json=SESSION_BODY).json()
    sid = created["session_id"]
    for position, item_id in enumerate(created["item_order"]):
        assert _response(client, sid, item_id, "yes", position).status_code == 200
    done = client.post(
        "/api/test/complete", json={"session_id": sid, "keep_score": False, "answered_count": 16}
    ).json()
    assert "need_resend" not in done
    assert done["correct_total"] == 8


def test_the_confirmed_answer_is_scored_and_the_trail_is_stored(client):
    created = client.post("/api/test/session", json=SESSION_BODY).json()
    sid = created["session_id"]
    first = created["item_order"][0]
    r = client.post(
        "/api/test/response",
        json={
            "session_id": sid,
            "item_id": first,
            "answer": "no",
            "rt_ms": 4200,
            "position": 0,
            "first_choice": "yes",
            "t_first_ms": 1100,
            "n_changes": 2,
        },
    )
    assert r.status_code == 200
    with Session(engine) as db:
        row = must(db.get(ItemResponse, (sid, first)))
    assert row.answer == "no"
    assert row.first_choice == "yes"
    assert row.t_first_ms == 1100
    assert row.n_changes == 2
    files = _read_zip(client.get("/api/test/export?token=test-export-token-1234567890").content)
    line = files["responses.csv"][0]
    assert line["final_choice"] == "no" and line["first_choice"] == "yes"
    assert line["t_confirm_ms"] == "4200" and line["t_first_ms"] == "1100"
    assert line["n_changes"] == "2"


# Demo -------------------------------------------------------------------------------------------


AFTER_LOCK = datetime(2026, 9, 28, 1, 0, 1, tzinfo=UTC)


def test_demo_answer_is_shut_before_the_lock(client):
    # Review finding F86: before the lock, sixteen answers would be the live test's key.
    freeze_now(AFTER_LOCK - timedelta(seconds=2))
    shut = client.post("/api/demo/answer", json={"item_id": "t01", "answer": "yes"})
    assert shut.status_code == 403
    assert shut.json() == {"detail": "Judge mode opens on Sep 28."}
    freeze_now(AFTER_LOCK)
    open_ = client.post("/api/demo/answer", json={"item_id": "t01", "answer": "yes"})
    assert open_.status_code == 200


def test_demo_answer_stores_nothing(client):
    freeze_now(AFTER_LOCK)
    before = {m: _count(m) for m in (StudySession, ItemResponse, ObserverRow)}
    with Session(engine) as db:
        counter_before = must(db.get(RandomizationCounter, 1)).next_position
    right = client.post("/api/demo/answer", json={"item_id": "t01", "answer": "yes"}).json()
    wrong = client.post("/api/demo/answer", json={"item_id": "t03", "answer": "yes"}).json()
    # Only whether they were right: sixteen of these would be the whole answer key.
    assert right == {"correct": True}
    assert wrong == {"correct": False}
    assert (
        client.post("/api/demo/answer", json={"item_id": "t99", "answer": "yes"}).status_code == 404
    )
    after = {m: _count(m) for m in (StudySession, ItemResponse, ObserverRow)}
    with Session(engine) as db:
        counter_after = must(db.get(RandomizationCounter, 1)).next_position
    assert before == after
    assert counter_before == counter_after


def test_content_hash(client):
    body = client.get("/api/content/hash").json()
    assert set(body) == {"content_hash", "build_hash"}
    assert len(body["content_hash"]) == 16
    assert body["build_hash"] == "test-build"


# Data lock --------------------------------------------------------------------------------------


def test_one_second_before_lock_is_a_normal_session(client):
    freeze_now(DATA_LOCK_UTC - timedelta(seconds=1))
    r = client.post("/api/test/session", json=SESSION_BODY)
    assert r.status_code == 200
    with Session(engine) as db:
        assert must(db.get(StudySession, r.json()["session_id"])).post_lock is False
    assert client.get("/api/test/counts").json()["post_lock"] == 0


def test_at_and_after_lock_sessions_are_marked_post_lock_and_still_answered(client):
    freeze_now(DATA_LOCK_UTC)
    at_lock = client.post("/api/test/session", json=SESSION_BODY)
    freeze_now(DATA_LOCK_UTC + timedelta(seconds=1))
    after = client.post("/api/test/session", json=SESSION_BODY)
    assert at_lock.status_code == after.status_code == 200
    assert set(after.json()) == {"session_id", "arm", "item_order", "lesson_first"}
    with Session(engine) as db:
        assert must(db.get(StudySession, at_lock.json()["session_id"])).post_lock is True
        assert must(db.get(StudySession, after.json()["session_id"])).post_lock is True
    done = full_session(client)
    assert done["correct_total"] >= 0
    assert client.get("/api/test/counts").json()["post_lock"] == 3
    files = _read_zip(client.get("/api/test/export?token=test-export-token-1234567890").content)
    assert all(row["post_lock"] == "1" for row in files["sessions.csv"])


def test_one_browser_keeps_one_arm_however_often_it_reloads(client):
    """Reloading must not let anyone shop for the trained arm: that would wreck the
    randomization the analysis plan pre-registered."""
    first = client.post("/api/test/session", json=visitor(99)).json()
    again = [client.post("/api/test/session", json=visitor(99)).json()["arm"] for _ in range(8)]
    assert set(again) == {first["arm"]}
    other = client.post("/api/test/session", json=visitor(100)).json()
    assert other["session_id"] != first["session_id"]
