"""Structured investigation reports with verifiable source excerpts."""

import json
from typing import Literal

from pydantic import BaseModel, Field

from .evidence import EvidenceLedger


class EvidenceItem(BaseModel):
    citation: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class InvestigationReport(BaseModel):
    hypothesis: str = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(min_length=1)
    alternatives: list[str] = Field(default_factory=list)
    confidence: Literal["低", "中", "高"]
    next_steps: list[str] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)

    def validate_sources(self, ledger: EvidenceLedger) -> list[str]:
        return [error for item in self.evidence if (error := ledger.validate_quote(item.citation, item.quote))]

    def render(self) -> str:
        lines = [f"根因假设：{self.hypothesis}", "支持证据："]
        lines.extend(f"- {item.explanation} {item.citation}（原文：{item.quote}）" for item in self.evidence)
        lines.append("其他可能：" + ("；".join(self.alternatives) if self.alternatives else "暂无"))
        lines.append(f"置信度：{self.confidence}")
        lines.append("下一步验证：" + "；".join(self.next_steps))
        if self.limitations:
            lines.append("局限：" + "；".join(self.limitations))
        return "\n".join(lines)


def parse_report(raw: str, ledger: EvidenceLedger) -> InvestigationReport:
    try:
        report = InvestigationReport.model_validate(json.loads(raw))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"报告不是符合约定字段的 JSON：{exc}") from exc
    errors = report.validate_sources(ledger)
    if errors:
        raise ValueError("；".join(errors))
    return report
