import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import investigate
from .repository import Repository, RepositoryError


app = FastAPI(title="Repo Sleuth API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"], allow_credentials=False)
RUNS: dict[str, dict] = {}
LOCK = threading.Lock()
DEMO_REPO = Path(__file__).resolve().parents[2] / "demo-repo"


class RunRequest(BaseModel):
    issue: str = Field(min_length=8, max_length=2000)
    repository: str = Field(min_length=1)
    demo: bool = False


def event(run_id: str, kind: str, title: str, detail: str) -> None:
    with LOCK:
        RUNS[run_id]["events"].append({"time": datetime.now(timezone.utc).isoformat(), "kind": kind, "title": title, "detail": detail})


def execute(run_id: str, repo: Repository, issue: str, demo: bool) -> None:
    try:
        if demo:
            event(run_id, "tool", "调用 list_files", "{}")
            event(run_id, "result", "list_files 返回", repo.list_files())
            event(run_id, "tool", "调用 read_file", '{"path":"calculator.py"}')
            event(run_id, "result", "read_file 返回", repo.read_file("calculator.py"))
            answer = "根因假设：calculator.py 第 5 行使用 int(a / b)，将非整除结果截断。例如 divide(5, 2) 得到 2，而预期为 2.5。建议改为 a / b，再针对非整除和除零输入补充测试。置信度：高。"
            event(run_id, "report", "调查结论（演示数据）", answer)
        else:
            answer = investigate(repo, issue, lambda kind, title, detail: event(run_id, kind, title, detail))
        with LOCK:
            RUNS[run_id]["answer"] = answer
            RUNS[run_id]["status"] = "completed"
    except Exception as exc:
        event(run_id, "error", "调查失败", str(exc))
        with LOCK:
            RUNS[run_id]["status"] = "failed"


@app.get("/api/health")
def health():
    return {"status": "ok", "api_key_configured": bool(os.getenv("OPENAI_API_KEY")), "demo_repository": str(DEMO_REPO)}


@app.post("/api/runs", status_code=202)
def create_run(request: RunRequest):
    if not request.demo and not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(400, "请先设置 OPENAI_API_KEY；或使用演示模式")
    try:
        repo = Repository(str(DEMO_REPO) if request.demo else request.repository)
    except RepositoryError as exc:
        raise HTTPException(400, str(exc)) from exc
    run_id = uuid4().hex
    with LOCK:
        RUNS[run_id] = {"id": run_id, "status": "running", "repository": str(repo.root), "issue": request.issue, "demo": request.demo, "events": [], "answer": None}
    threading.Thread(target=execute, args=(run_id, repo, request.issue, request.demo), daemon=True).start()
    return {"id": run_id}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    with LOCK:
        run = RUNS.get(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在")
        return dict(run, events=list(run["events"]))
