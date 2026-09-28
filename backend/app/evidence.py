"""Track which source lines the agent actually observed before citing them."""

import re


CITATION = re.compile(r"\[([^\[\]\n]+):(\d+)\]")
SEARCH_HIT = re.compile(r"^(.+?):(\d+):")


class EvidenceLedger:
    def __init__(self):
        self.lines: set[tuple[str, int]] = set()
        self.content: dict[tuple[str, int], str] = {}

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, str]) -> "EvidenceLedger":
        ledger = cls()
        for citation, content in snapshot.items():
            match = CITATION.fullmatch(citation)
            if match:
                key = (match.group(1), int(match.group(2)))
                ledger.lines.add(key)
                ledger.content[key] = content
        return ledger

    def snapshot(self) -> dict[str, str]:
        return {f"[{path}:{number}]": content for (path, number), content in self.content.items()}

    def record(self, name: str, arguments: dict, result: str) -> None:
        if result.startswith("工具错误："):
            return
        if name == "read_file":
            path = arguments.get("path")
            if isinstance(path, str):
                for line in result.splitlines():
                    match = re.match(r"^(\d+) \| ", line)
                    if match:
                        key = (path.removeprefix("./"), int(match.group(1)))
                        self.lines.add(key)
                        self.content[key] = line[match.end():]
        elif name == "search_code":
            for line in result.splitlines():
                match = SEARCH_HIT.match(line)
                if match:
                    key = (match.group(1).removeprefix("./"), int(match.group(2)))
                    self.lines.add(key)
                    self.content[key] = line[match.end():]

    def validate(self, answer: str) -> list[str]:
        citations = CITATION.findall(answer)
        if not citations:
            return ["结论缺少 [文件路径:行号] 引用"]
        invalid = [f"[{path}:{number}]" for path, number in citations if (path.removeprefix("./"), int(number)) not in self.lines]
        return [f"引用未在工具证据中出现：{', '.join(invalid)}"] if invalid else []

    @property
    def citation_count(self) -> int:
        return len(self.lines)

    def validate_quote(self, citation: str, quote: str) -> str | None:
        match = CITATION.fullmatch(citation)
        if not match:
            return f"引用格式错误：{citation}"
        key = (match.group(1).removeprefix("./"), int(match.group(2)))
        source = self.content.get(key)
        if source is None:
            return f"引用未在工具证据中出现：{citation}"
        if not quote.strip() or quote.strip() not in source:
            return f"引用原文与实际代码不符：{citation}"
        return None
