import json
from collections.abc import Iterable
from pathlib import Path

from codebase_agent.config import settings
from codebase_agent.ingestion.models import SourceFile


def build_file_sources(sources: Iterable[SourceFile]) -> dict[str, str]:
    """Map every ingested file's path to its full text.

    Symbol-bounded snippets (see snippets.py) don't cover text outside any
    symbol's body - module-level comments, blank lines between functions, a
    file with no symbols at all - so whole-repo text scans (TODO extraction)
    need the complete file, not just the concatenation of its symbols.
    """
    return {s.path: s.content for s in sources}


class FileSourceStore:
    """Persists the file_path -> full text map as JSON, one file per repo."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or settings.knowledge_dir

    def save(self, repo_name: str, sources: dict[str, str]) -> None:
        repo_dir = self._repo_dir(repo_name)
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "files.json").write_text(
            json.dumps(sources, indent=2), encoding="utf-8"
        )

    def load(self, repo_name: str) -> dict[str, str]:
        path = self._repo_dir(repo_name) / "files.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _repo_dir(self, repo_name: str) -> Path:
        return self._base_dir / repo_name
