"""Read-only repository tools. Model arguments never become shell commands."""

from pathlib import Path
import subprocess


MAX_OUTPUT = 12_000
MAX_FILE_BYTES = 24_000


class RepositoryError(ValueError):
    pass


class Repository:
    def __init__(self, root: str):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise RepositoryError("仓库目录不存在")

    def _path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if not candidate.is_relative_to(self.root) or candidate == self.root:
            raise RepositoryError("文件路径必须位于仓库内")
        if not candidate.is_file():
            raise RepositoryError("文件不存在")
        return candidate

    def list_files(self) -> str:
        result = subprocess.run(
            ["rg", "--files", "--hidden", "-g", "!.git", "-g", "!node_modules", "-g", "!.venv"],
            cwd=self.root, capture_output=True, text=True, timeout=8, check=False,
        )
        if result.returncode not in (0, 1):
            raise RepositoryError(result.stderr.strip() or "无法列出文件")
        return result.stdout[:MAX_OUTPUT] or "仓库中没有可见文件"

    def search_code(self, query: str) -> str:
        if not query or len(query) > 120:
            raise RepositoryError("搜索词长度需为 1–120 个字符")
        result = subprocess.run(
            ["rg", "-n", "-F", "--hidden", "-m", "8", "-g", "!.git", "-g", "!node_modules", "-g", "!.venv", "--", query, "."],
            cwd=self.root, capture_output=True, text=True, timeout=8, check=False,
        )
        if result.returncode not in (0, 1):
            raise RepositoryError(result.stderr.strip() or "搜索失败")
        return result.stdout[:MAX_OUTPUT] or "没有匹配结果"

    def read_file(self, path: str) -> str:
        target = self._path(path)
        if target.stat().st_size > MAX_FILE_BYTES:
            raise RepositoryError("文件过大，请先缩小调查范围")
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise RepositoryError("仅支持 UTF-8 文本文件") from exc


TOOLS = [
    {"type": "function", "name": "list_files", "description": "列出仓库中的文件。", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "search_code", "description": "在仓库中按字面文本搜索并返回文件和行号。", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "read_file", "description": "读取一个仓库内 UTF-8 文本文件。", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}, "strict": True},
]


def run_tool(repo: Repository, name: str, arguments: dict) -> str:
    try:
        if name == "list_files":
            return repo.list_files()
        if name == "search_code":
            return repo.search_code(arguments["query"])
        if name == "read_file":
            return repo.read_file(arguments["path"])
        return "工具不存在"
    except (RepositoryError, KeyError, TypeError) as exc:
        return f"工具错误：{exc}"
