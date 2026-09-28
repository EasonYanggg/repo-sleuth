import os
import threading
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import investigate
from .demo import SCENARIOS, run_demo
from .repository import Repository, RepositoryError
from .store import RunStore


app = FastAPI(title="Repo Sleuth API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"], allow_credentials=False)
DEMO_REPO = Path(__file__).resolve().parents[2] / "demo-repo"
STORE = RunStore(Path(os.getenv("REPO_SLEUTH_DB", str(Path(__file__).resolve().parents[1] / "data" / "runs.sqlite"))))


class RunRequest(BaseModel):
    issue: str = Field(min_length=8, max_length=2000)
    repository: str = Field(min_length=1)
    demo: bool = False
    scenario: Literal["division", "threshold"] = "division"


def event(run_id: str, kind: str, title: str, detail: str) -> None:
    STORE.event(run_id, kind, title, detail)


def execute(run_id: str, repo: Repository, issue: str, demo: bool, scenario: str) -> None:
    try:
        if demo:
            answer = run_demo(repo, scenario, lambda kind, title, detail: event(run_id, kind, title, detail))
        else:
            answer = investigate(repo, issue, lambda kind, title, detail: event(run_id, kind, title, detail))
        STORE.finish(run_id, "completed", answer)
    except Exception as exc:
        event(run_id, "error", "调查失败", str(exc))
        STORE.finish(run_id, "failed")


@app.get("/api/health")
def health():
    return {"status": "ok", "api_key_configured": bool(os.getenv("OPENAI_API_KEY")), "demo_repository": str(DEMO_REPO)}


@app.get("/api/scenarios")
def scenarios():
    return [{"id": key, "title": value["title"], "issue": value["issue"]} for key, value in SCENARIOS.items()]


@app.get("/api/runs")
def list_runs():
    return STORE.list()


@app.post("/api/runs", status_code=202)
def create_run(request: RunRequest):
    if not request.demo and not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(400, "请先设置 OPENAI_API_KEY；或使用演示模式")
    try:
        repo = Repository(str(DEMO_REPO) if request.demo else request.repository)
    except RepositoryError as exc:
        raise HTTPException(400, str(exc)) from exc
    run_id = uuid4().hex
    STORE.create(run_id, str(repo.root), request.issue, request.demo, request.scenario if request.demo else None)
    threading.Thread(target=execute, args=(run_id, repo, request.issue, request.demo, request.scenario), daemon=True).start()
    return {"id": run_id}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = STORE.get(run_id)
    if run is None:
        raise HTTPException(404, "任务不存在")
    return run
