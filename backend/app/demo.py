"""Deterministic demonstrations using the same read-only tools and citation checks."""

import json
from typing import Callable

from .evidence import EvidenceLedger
from .report import InvestigationReport
from .repository import Repository, run_tool


SCENARIOS = {
    "division": {
        "title": "小数除法结果被截断",
        "issue": "divide(5, 2) 返回 2，但预期是 2.5。请定位原因。",
        "path": "calculator.py",
        "query": "int(a / b)",
        "report": {
            "hypothesis": "divide 将除法结果转为整数，导致小数部分丢失。",
            "evidence": [{"citation": "[calculator.py:5]", "quote": "return int(a / b)", "explanation": "int 把 2.5 截断为 2。"}],
            "alternatives": ["调用方显示格式问题；当前代码证据更支持整数转换。"],
            "confidence": "高",
            "next_steps": ["改为 a / b，并补充非整除和除零边界测试。"],
            "limitations": ["演示模式没有实际运行测试。"],
        },
    },
    "threshold": {
        "title": "免运费边界值判断错误",
        "issue": "订单金额正好为 100 时仍收取运费，但业务规则是满 100 免运费。请定位原因。",
        "path": "shipping.py",
        "query": "order_total > 100",
        "report": {
            "hypothesis": "免运费条件使用严格大于号，遗漏金额恰好为 100 的订单。",
            "evidence": [
                {"citation": "[shipping.py:2]", "quote": "100 or more", "explanation": "文档说明 100 及以上应免运费。"},
                {"citation": "[shipping.py:3]", "quote": "order_total > 100", "explanation": "条件将恰好 100 排除在免运费之外。"},
            ],
            "alternatives": ["上游金额四舍五入问题；当前边界条件本身已足以解释现象。"],
            "confidence": "高",
            "next_steps": ["改为 >= 100，并测试 99.99、100、100.01。"],
            "limitations": ["演示模式没有实际运行测试。"],
        },
    },
}


def _simple_scenario(title: str, issue: str, path: str, query: str, hypothesis: str,
                     citation: str, quote: str, explanation: str, next_step: str) -> dict:
    return {
        "title": title, "issue": issue, "path": path, "query": query,
        "report": {
            "hypothesis": hypothesis,
            "evidence": [{"citation": citation, "quote": quote, "explanation": explanation}],
            "alternatives": [], "confidence": "高", "next_steps": [next_step],
            "limitations": ["演示模式没有实际运行测试。"],
        },
    }


SCENARIOS.update({
    "mutable_default": _simple_scenario(
        "可变默认参数污染下一次调用", "第二次 add_tag 调用包含第一次的标签，为什么？",
        "cache.py", "tags: list[str] = []", "默认列表在函数定义时创建并被多次调用共享。",
        "[cache.py:1]", "tags: list[str] = []", "可变默认参数会保留前一次追加的标签。",
        "改用 None 作为默认值，并在函数内新建列表。"),
    "pagination": _simple_scenario(
        "分页少返回一个元素", "page(items, 0, 10) 只返回 9 个元素，为什么？",
        "pagination.py", "start + size - 1", "切片结束位置多减了 1，造成分页少一个元素。",
        "[pagination.py:3]", "start + size - 1", "Python 切片结束位置不包含在结果中。",
        "改为 items[start:start + size] 并测试首尾页。"),
    "authorization": _simple_scenario(
        "授权条件放行非管理员", "非管理员但 active=True 的用户能够访问管理页，为什么？",
        "auth.py", "role != \"admin\" and not active", "拒绝条件使用 and，非管理员只要 active 就会被放行。",
        "[auth.py:3]", "role != \"admin\" and not active", "两个违规条件必须同时成立才会拒绝访问。",
        "改为 role != 'admin' or not active，并覆盖权限矩阵测试。"),
    "retry": _simple_scenario(
        "重试次数多一次", "max_attempts=3 时循环执行了 4 次，为什么？",
        "retry.py", "attempts <= max_attempts", "循环条件使用 <=，包含了第四次重试。",
        "[retry.py:4]", "attempts <= max_attempts", "从 0 开始计数时，0、1、2、3 共四次。",
        "改为 < 并测试 0、1、3 次的边界。"),
    "normalization": _simple_scenario(
        "文本标准化返回方法对象", "normalize(' A ') 返回方法对象而不是 'a'，为什么？",
        "normalize.py", "value.strip().lower", "lower 缺少调用括号，返回绑定方法而不是字符串。",
        "[normalize.py:3]", "value.strip().lower", "代码访问 lower 属性，但没有执行 lower()。",
        "改为 value.strip().lower() 并检查返回类型。"),
    "boolean_env": _simple_scenario(
        "环境变量 false 仍启用功能", "FEATURE_ENABLED=false 时 feature_enabled() 仍返回 True，为什么？",
        "config.py", "bool(os.getenv", "非空字符串 'false' 经 bool 转换仍为 True。",
        "[config.py:6]", "bool(os.getenv(\"FEATURE_ENABLED\", \"false\"))", "bool 判断字符串是否为空，不解析布尔语义。",
        "显式比较环境变量的小写值与 'true'。"),
    "sorting": _simple_scenario(
        "排序函数返回 None", "sorted_users 返回 None，但列表确实被排序了，为什么？",
        "sorting.py", "return users.sort", "list.sort 原地排序并返回 None，导致函数也返回 None。",
        "[sorting.py:3]", "return users.sort", "直接返回原地排序方法的结果。",
        "改为 return sorted(users, key=...) 或排序后返回 users。"),
    "tax_rate": _simple_scenario(
        "百分比税率被当成小数", "rate=8 时税后总价变成原价的 9 倍，为什么？",
        "tax.py", "1 + rate", "百分比税率未除以 100，8 被当成 800%。",
        "[tax.py:3]", "subtotal * (1 + rate)", "税额计算直接加 8，而不是加 0.08。",
        "改为 subtotal * (1 + rate / 100)，测试 0、8、100。"),
})


def run_demo_report(repo: Repository, scenario: str, emit: Callable[[str, str, str], None]) -> InvestigationReport:
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
    report = InvestigationReport.model_validate(config["report"])
    answer = report.render()
    errors = ledger.validate(answer) + report.validate_sources(ledger)
    if errors:
        raise RuntimeError("演示证据校验失败：" + "；".join(errors))
    emit("verification", "证据引用与原文已核验", f"已观察 {ledger.citation_count} 行可引用证据；逻辑推断仍需人工审查")
    emit("report", "调查结论（确定性演示）", answer)
    return report


def run_demo(repo: Repository, scenario: str, emit: Callable[[str, str, str], None]) -> str:
    return run_demo_report(repo, scenario, emit).render()
