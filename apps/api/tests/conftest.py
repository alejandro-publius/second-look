"""Test setup. A file backed SQLite database in a temp folder, so threads get their own
connections. Environment is set before the app is imported, because settings are read once."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="sl-api-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["EXPORT_TOKEN"] = "test-export-token-1234567890"
os.environ["QA_KEY"] = "test-qa-key-1234567890abcd"
os.environ["PUBLIC_WEB_ORIGIN"] = "http://web.test"
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["FHIR_STORE_DIR"] = str(_TMP / "fhir_store")
os.environ["RANDOMIZATION_SEED"] = "test-seed"
os.environ["BUILD_HASH"] = "test-build"
os.environ["AUDIT_LOG_PATH"] = str(_TMP / "audit.jsonl")

from fastapi.testclient import TestClient  # noqa: E402

from apps.api import deps  # noqa: E402
from apps.api.db import reset_db  # noqa: E402
from apps.api.main import app  # noqa: E402
from apps.api.security import reset_rate_limits  # noqa: E402

SESSION_BODY = {
    "consent_version": "v1",
    "content_hash": "abc",
    "build_hash": "test-build",
    "source_label": "poster",
    "hidden_field": "",
    "client_token_hash": "0123456789abcdef0123456789abcdef",
    "ua_class": "phone",
    "warmup_choice": "w01",
}


@pytest.fixture
def client() -> Iterator[TestClient]:
    reset_db()
    reset_rate_limits()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def freeze_now(moment: datetime) -> None:
    app.dependency_overrides[deps.get_now] = lambda: moment


def full_session(client: TestClient, *, keep_score: bool = False, answer: str = "yes") -> dict:
    """Consent, session, 16 answers, complete. Returns the complete response plus session_id."""
    created = client.post("/api/test/session", json=SESSION_BODY).json()
    sid = created["session_id"]
    for position, item_id in enumerate(created["item_order"]):
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
        "/api/test/complete",
        json={"session_id": sid, "prior_experience": "no", "keep_score": keep_score},
    )
    assert done.status_code == 200, done.text
    out = done.json()
    out["session_id"] = sid
    out["arm"] = created["arm"]
    return out
