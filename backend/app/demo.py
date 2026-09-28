"""Deterministic demonstrations using the same read-only tools and citation checks."""

import json
from typing import Callable

from .evidence import EvidenceLedger
from .repository import Repository, run_tool


SCENARIOS = {
    "division": {
        "title": "小数除法结果被截断",
        "issue": "divide(5, 2) 返回 2，但预期是 2.5。请定位原因。",
        "path": "calculator.py",
        "query": "int(a / b)",
        "answer": "根因假设：`divide` 把除法结果交给 `int`，非整数部分被截断 [calculator.py:5]。`divide(5, 2)` 因此得到 2，而不是 2.5。置信度：高。下一步：将表达式改为 `a / b`，并补充非整除和除零边界测试。",
    },
    "threshold": {
        "title": "免运费边界值判断错误",
        "issue": "订单金额正好为 100 时仍收取运费，但业务规则是满 100 免运费。请定位原因。",
        "path": "shipping.py",
        "query": "order_total > 100",
        "answer": "根因假设：文档要求金额达到 100 即免运费 [shipping.py:2]，但条件使用了严格大于号，排除了恰好 100 的订单 [shipping.py:3]。置信度：高。下一步：改为 `>= 100`，测试 99.99、100 和 100.01 三个边界值。",
    },
}


def run_demo(repo: Repository, scenario: str, emit: Callable[[str, str, str], None]) -> str:
    if scenario not in SCENARIOS:
        raise ValueError("未知演示场景")
    config = SCENARIOS[scenario]
    ledger = EvidenceLedger()
    steps = [("list_files", {}), ("search_code", {"query": config["query"]}), ("read_file", {"path": config["path"]})]
    for name, arguments in steps:
        emit("tool", f"调用 {name}", json.dumps(arguments, ensure_ascii=False))
        result = run_tool(repo, name, arguments)
        ledger.record(name, arguments, result)
        emit("result", f"{name} 返回", result[:2000])
    answer = config["answer"]
    errors = ledger.validate(answer)
    if errors:
        raise RuntimeError("演示证据校验失败：" + "；".join(errors))
    emit("verification", "证据引用已核验", f"已观察 {ledger.citation_count} 行可引用证据")
    emit("report", "调查结论（确定性演示）", answer)
    return answer
