import time

from fastapi.testclient import TestClient
import pytest

import app.main as main
from app.main import app
from app.store import RunStore


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORE", RunStore(tmp_path / "runs.sqlite"))


def test_demo_run_completes():
    client = TestClient(app)
    created = client.post("/api/runs", json={"issue": "divide(5, 2) returns 2", "repository": "unused", "demo": True})
    assert created.status_code == 202
    run_id = created.json()["id"]
    for _ in range(30):
        result = client.get(f"/api/runs/{run_id}")
        assert result.status_code == 200
        if result.json()["status"] != "running":
            break
        time.sleep(0.01)
    data = result.json()
    assert data["status"] == "completed"
    assert data["answer"]
    assert [event["kind"] for event in data["events"]] == ["tool", "result", "tool", "result", "tool", "result", "verification", "report"]
    assert client.get("/api/runs").json()[0]["id"] == run_id


def test_threshold_scenario_has_verified_citations():
    client = TestClient(app)
    created = client.post("/api/runs", json={"issue": "100 should ship free", "repository": "unused", "demo": True, "scenario": "threshold"})
    assert created.status_code == 202
    run_id = created.json()["id"]
    for _ in range(30):
        data = client.get(f"/api/runs/{run_id}").json()
        if data["status"] != "running":
            break
        time.sleep(0.01)
    assert data["status"] == "completed"
    assert "[shipping.py:3]" in data["answer"]
    assert any(item["kind"] == "verification" for item in data["events"])
