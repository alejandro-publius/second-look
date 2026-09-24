"""The panel study's source label (UPDATE_29 section 1): stored as "panel", counted as "panel"."""

from __future__ import annotations

from apps.api import study
from apps.api.tests.conftest import SESSION_BODY


def test_a_panel_session_is_stored_and_counted_as_panel(client):
    body = {**SESSION_BODY, "source_label": "panel"}
    created = client.post("/api/test/session", json=body).json()
    sid = created["session_id"]
    for position, item_id in enumerate(created["item_order"]):
        client.post(
            "/api/test/response",
            json={
                "session_id": sid,
                "item_id": item_id,
                "answer": "no",
                "rt_ms": 900,
                "position": position,
            },
        )
    done = client.post(
        "/api/test/complete",
        json={
            "session_id": sid,
            "prior_experience": "no",
            "keep_score": False,
            "answered_count": 16,
        },
    )
    assert done.status_code == 200, done.text
    counts = client.get("/api/test/counts").json()
    assert counts["by_source"]["panel"] == 1
    assert sum(counts["by_source"].values()) == 1


def test_only_the_known_labels_are_kept():
    assert study.coerce_source("panel") == "panel"
    assert study.coerce_source("PROLIFIC_PID=abc") == "other"
    assert study.coerce_source(None) == "other"
