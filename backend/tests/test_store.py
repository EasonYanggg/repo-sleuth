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


def test_running_task_is_marked_interrupted_after_restart(tmp_path):
    path = tmp_path / "runs.sqlite"
    first = RunStore(path)
    first.create("pending", "/repo", "bug", True, "division")
    second = RunStore(path)
    run = second.get("pending")
    assert run["status"] == "failed"
    assert run["events"][-1]["title"] == "调查中断"
