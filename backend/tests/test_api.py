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
    assert data["report"]["evidence"][0]["quote"] == "return int(a / b)"
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


def test_new_scenario_is_accepted():
    client = TestClient(app)
    created = client.post("/api/runs", json={"issue": "第二次 add_tag 调用包含第一次的标签，为什么？", "repository": "unused", "demo": True, "scenario": "mutable_default"})
    assert created.status_code == 202
    run_id = created.json()["id"]
    for _ in range(30):
        data = client.get(f"/api/runs/{run_id}").json()
        if data["status"] != "running":
            break
        time.sleep(0.01)
    assert data["status"] == "completed"
    assert data["report"]["evidence"][0]["citation"] == "[cache.py:1]"


def test_unknown_demo_scenario_is_rejected():
    client = TestClient(app)
    response = client.post("/api/runs", json={"issue": "Unknown scenario", "repository": "unused", "demo": True, "scenario": "missing"})
    assert response.status_code == 400


def test_startup_recovers_unfinished_demo_run():
    main.STORE.create("pending-demo", str(main.DEMO_REPO), "divide(5, 2) returns 2", True, "division")
    with TestClient(app) as client:
        for _ in range(50):
            data = client.get("/api/runs/pending-demo").json()
            if data["status"] != "running":
                break
            time.sleep(0.01)
    assert data["status"] == "completed"
    assert any(item["title"] == "恢复调查" for item in data["events"])
