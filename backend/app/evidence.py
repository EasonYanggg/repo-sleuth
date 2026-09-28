"""Track which source lines the agent actually observed before citing them."""

import re


CITATION = re.compile(r"\[([^\[\]\n]+):(\d+)\]")
SEARCH_HIT = re.compile(r"^(.+?):(\d+):")


class EvidenceLedger:
    def __init__(self):
        self.lines: set[tuple[str, int]] = set()

    def record(self, name: str, arguments: dict, result: str) -> None:
        if result.startswith("工具错误："):
            return
        if name == "read_file":
            path = arguments.get("path")
            if isinstance(path, str):
                for line in result.splitlines():
                    match = re.match(r"^(\d+) \| ", line)
                    if match:
                        self.lines.add((path, int(match.group(1))))
        elif name == "search_code":
            for line in result.splitlines():
                match = SEARCH_HIT.match(line)
                if match:
                    self.lines.add((match.group(1).removeprefix("./"), int(match.group(2))))

    def validate(self, answer: str) -> list[str]:
        citations = CITATION.findall(answer)
        if not citations:
            return ["结论缺少 [文件路径:行号] 引用"]
        invalid = [f"[{path}:{number}]" for path, number in citations if (path.removeprefix("./"), int(number)) not in self.lines]
        return [f"引用未在工具证据中出现：{', '.join(invalid)}"] if invalid else []

    @property
    def citation_count(self) -> int:
        return len(self.lines)
