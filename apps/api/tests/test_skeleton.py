import os

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient  # noqa: E402

from apps.api.main import app  # noqa: E402


def test_health_and_ping_round_trip():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        first = client.post("/api/skeleton/ping").json()["rows"]
        second = client.post("/api/skeleton/ping").json()["rows"]
        assert second == first + 1
