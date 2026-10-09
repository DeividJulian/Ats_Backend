def test_statistics_with_demo_data(client, demo_data):
    stats = client.get("/stats").json()
    assert stats["totals"] == {"jobs": 3, "open_jobs": 3, "candidates": 9, "applications": 10}
    assert sum(stats["funnel"].values()) == 10
    assert len(stats["per_job"]) == 3
    assert stats["most_demanded_skills"]


def test_statistics_without_data(client):
    stats = client.get("/stats").json()
    assert stats["totals"]["applications"] == 0
    assert stats["hire_rate_pct"] == 0.0


def test_hiring_rate(client, demo_data):
    for status in ("shortlisted", "interview", "offer", "hired"):
        client.patch("/applications/3/status", json={"status": status})
    assert client.get("/stats").json()["hire_rate_pct"] == 10.0


def test_seed_does_not_overwrite_without_reset(client, demo_data):
    assert client.post("/seed").status_code == 409
    assert client.post("/seed?reset=true").status_code == 200
    assert len(client.get("/candidates").json()) == demo_data["candidates"]
