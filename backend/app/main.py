import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import investigate_report
from .demo import SCENARIOS, run_demo_report
from .repository import Repository, RepositoryError
from .store import RunStore


@asynccontextmanager
async def lifespan(_: FastAPI):
    resume_unfinished_runs()
    yield


app = FastAPI(title="Repo Sleuth API", version="0.3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"], allow_credentials=False)
DEMO_REPO = Path(__file__).resolve().parents[2] / "demo-repo"
STORE = RunStore(Path(os.getenv("REPO_SLEUTH_DB", str(Path(__file__).resolve().parents[1] / "data" / "runs.sqlite"))))
CHECKPOINTS = Path(os.getenv("REPO_SLEUTH_CHECKPOINT_DB", str(Path(__file__).resolve().parents[1] / "data" / "checkpoints.sqlite")))


class RunRequest(BaseModel):
    issue: str = Field(min_length=8, max_length=2000)
    repository: str = Field(min_length=1)
    demo: bool = False
    scenario: str = Field(default="division", max_length=64)


def event(run_id: str, kind: str, title: str, detail: str) -> None:
    STORE.event(run_id, kind, title, detail)


def execute(run_id: str, repo: Repository, issue: str, demo: bool, scenario: str, resume: bool = False) -> None:
    try:
        if resume:
            detail = "演示模式将重新运行只读步骤" if demo else "从持久化检查点继续；已完成的图节点不会整体重跑"
            event(run_id, "stage", "恢复调查", detail)
        if demo:
            report = run_demo_report(repo, scenario, lambda kind, title, detail: event(run_id, kind, title, detail))
        else:
            report = investigate_report(repo, issue, lambda kind, title, detail: event(run_id, kind, title, detail), run_id=run_id, checkpoint_path=CHECKPOINTS, resume=resume)
        STORE.finish(run_id, "completed", report.render(), report.model_dump())
    except Exception as exc:
        event(run_id, "error", "调查失败", str(exc))
        STORE.finish(run_id, "failed")


def resume_unfinished_runs() -> None:
    for pending in STORE.running():
        try:
            if not pending["demo"] and not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("缺少 OPENAI_API_KEY，无法恢复真实调查")
            repo = Repository(pending["repository"])
        except (RepositoryError, RuntimeError) as exc:
            event(pending["id"], "error", "恢复失败", str(exc))
            STORE.finish(pending["id"], "failed")
            continue
        threading.Thread(
            target=execute,
            args=(pending["id"], repo, pending["issue"], bool(pending["demo"]), pending["scenario"] or "division", True),
            daemon=True,
        ).start()


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
    if request.demo and request.scenario not in SCENARIOS:
        raise HTTPException(400, "未知演示场景")
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
