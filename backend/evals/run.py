"""Tiny, reproducible benchmark for evidence quality and tool behavior.

Run from backend/: python -m evals.run [--live] [--output report.json]
"""

import argparse
import json
import os
from pathlib import Path

from app.agent import investigate
from app.demo import run_demo
from app.repository import Repository


BASE = Path(__file__).resolve().parents[2]
CASES = Path(__file__).with_name("cases.json")


def evaluate(live=False):
    if live and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("真实评测需要 OPENAI_API_KEY")
    repo = Repository(str(BASE / "demo-repo"))
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        events = []
        emit = lambda kind, title, detail: events.append({"kind": kind, "title": title, "detail": detail})
        try:
            answer = investigate(repo, case["issue"], emit) if live else run_demo(repo, case["id"], emit)
            checks = {
                "expected_citations": all(citation in answer for citation in case["expected_citations"]),
                "expected_terms": all(term in answer for term in case["expected_terms"]),
                "tool_used": any(event["kind"] == "tool" for event in events),
                "citations_verified": any(event["kind"] == "verification" and "已核验" in event["title"] for event in events),
            }
            results.append({"id": case["id"], "passed": all(checks.values()), "checks": checks, "tool_calls": sum(event["kind"] == "tool" for event in events), "answer": answer})
        except Exception as exc:
            results.append({"id": case["id"], "passed": False, "error": str(exc)})
    return {"mode": "live" if live else "demo", "passed": sum(item["passed"] for item in results), "total": len(results), "cases": results}


def main():
    parser = argparse.ArgumentParser(description="Evaluate Repo Sleuth against annotated bug cases")
    parser.add_argument("--live", action="store_true", help="Call the configured OpenAI model; consumes API usage")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    report = evaluate(live=args.live)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
