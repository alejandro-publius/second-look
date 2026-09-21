def test_health_and_ping_round_trip(client):
    assert client.get("/health").json() == {"status": "ok"}
    first = client.post("/api/skeleton/ping").json()["rows"]
    second = client.post("/api/skeleton/ping").json()["rows"]
    assert second == first + 1
