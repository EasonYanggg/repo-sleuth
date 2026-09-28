import time

from fastapi.testclient import TestClient

from app.main import app


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
    assert [event["kind"] for event in data["events"]] == ["tool", "result", "tool", "result", "report"]
