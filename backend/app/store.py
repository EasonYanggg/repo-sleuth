"""Product-facing run history; graph execution checkpoints live separately."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, repository TEXT NOT NULL,
                issue TEXT NOT NULL, demo INTEGER NOT NULL, scenario TEXT,
                answer TEXT, report TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                time TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS events_run_id ON events(run_id, id)")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(runs)")}
            if "report" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN report TEXT")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, run_id: str, repository: str, issue: str, demo: bool, scenario: Optional[str]):
        timestamp = now()
        with self.connect() as db:
            db.execute("INSERT INTO runs (id, status, repository, issue, demo, scenario, answer, report, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (run_id, "running", repository, issue, int(demo), scenario, None, None, timestamp, timestamp))

    def event(self, run_id: str, kind: str, title: str, detail: str):
        with self.connect() as db:
            db.execute("INSERT INTO events (run_id, time, kind, title, detail) VALUES (?, ?, ?, ?, ?)",
                       (run_id, now(), kind, title, detail))
            db.execute("UPDATE runs SET updated_at = ? WHERE id = ?", (now(), run_id))

    def finish(self, run_id: str, status: str, answer: Optional[str] = None, report: Optional[dict] = None):
        with self.connect() as db:
            db.execute("UPDATE runs SET status = ?, answer = ?, report = ?, updated_at = ? WHERE id = ?",
                       (status, answer, json.dumps(report, ensure_ascii=False) if report else None, now(), run_id))

    def get(self, run_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            events = db.execute("SELECT time, kind, title, detail FROM events WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
        result = dict(row)
        result["demo"] = bool(result["demo"])
        result["report"] = json.loads(result["report"]) if result["report"] else None
        result["events"] = [dict(event) for event in events]
        return result

    def running(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT id, repository, issue, demo, scenario FROM runs WHERE status = 'running'")]

    def list(self, limit: int = 20):
        with self.connect() as db:
            rows = db.execute("SELECT id, status, repository, issue, demo, scenario, created_at, updated_at FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row, demo=bool(row["demo"])) for row in rows]
