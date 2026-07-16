import json
from collections.abc import Iterable
from pathlib import Path

from codebase_agent.config import settings
from codebase_agent.ingestion.models import SourceFile
from codebase_agent.intelligence.models import RepoStructure


def build_symbol_sources(
    structure: RepoStructure, sources: Iterable[SourceFile]
) -> dict[str, str]:
    """Slice each symbol's exact source text out of its file.

    Computed once at ingestion time, while file contents are already in
    memory, so `KnowledgeBase.get_source` can serve exact symbol text later
    without depending on the original checkout still being on disk.
    """
    content_by_file = {s.path: s.content for s in sources}
    result: dict[str, str] = {}
    for symbol in structure.symbols:
        content = content_by_file.get(symbol.file_path)
        if content is None:
            continue
        result[symbol.qualified_name] = _slice_lines(
            content, symbol.start_line, symbol.end_line
        )
    return result


def _slice_lines(content: str, start_line: int, end_line: int) -> str:
    lines = content.splitlines()
    return "\n".join(lines[start_line - 1 : end_line])


class SymbolSourceStore:
    """Persists the qualified_name -> source text map as JSON, one file per repo."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or settings.knowledge_dir

    def save(self, repo_name: str, sources: dict[str, str]) -> None:
        repo_dir = self._repo_dir(repo_name)
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "sources.json").write_text(
            json.dumps(sources, indent=2), encoding="utf-8"
        )

    def load(self, repo_name: str) -> dict[str, str]:
        path = self._repo_dir(repo_name) / "sources.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _repo_dir(self, repo_name: str) -> Path:
        return self._base_dir / repo_name
