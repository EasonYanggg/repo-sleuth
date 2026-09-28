from app.store import RunStore


def test_runs_survive_store_reopen(tmp_path):
    path = tmp_path / "runs.sqlite"
    first = RunStore(path)
    first.create("r1", "/repo", "bug", True, "division")
    first.event("r1", "tool", "list_files", "{}")
    first.finish("r1", "completed", "answer")
    second = RunStore(path)
    run = second.get("r1")
    assert run["answer"] == "answer"
    assert run["events"][0]["title"] == "list_files"
    assert second.list()[0]["id"] == "r1"


def test_legacy_database_gains_report_column(tmp_path):
    import sqlite3

    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE runs (id TEXT PRIMARY KEY, status TEXT NOT NULL, repository TEXT NOT NULL, issue TEXT NOT NULL, demo INTEGER NOT NULL, scenario TEXT, answer TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    store = RunStore(path)
    store.create("r1", "/repo", "bug", True, "division")
    store.finish("r1", "completed", "answer", {"hypothesis": "bug"})
    assert store.get("r1")["report"]["hypothesis"] == "bug"


def test_running_task_remains_available_for_recovery(tmp_path):
    path = tmp_path / "runs.sqlite"
    first = RunStore(path)
    first.create("pending", "/repo", "bug", True, "division")
    second = RunStore(path)
    run = second.get("pending")
    assert run["status"] == "running"
    assert second.running()[0]["id"] == "pending"
