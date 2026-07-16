import json
from dataclasses import asdict
from pathlib import Path

from codebase_agent.config import settings
from codebase_agent.intelligence.models import (
    CallEdge,
    ImportEdge,
    InheritsEdge,
    RepoStructure,
    Symbol,
)


class RepoIntelligenceStore:
    """Persists a repo's extracted structure as JSON, one directory per repo.

    JSON + in-memory NetworkX is enough at portfolio scale (a repo's worth of
    symbols and edges, not a monorepo) and keeps the artifacts human-readable.
    If that stops being true, this class's interface (save/load/has_repo) is
    the seam to swap in a real database behind - callers don't need to change.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or settings.graph_dir

    def save(self, repo_name: str, structure: RepoStructure) -> None:
        repo_dir = self._repo_dir(repo_name)
        repo_dir.mkdir(parents=True, exist_ok=True)

        symbols_path = repo_dir / "symbols.json"
        symbols_path.write_text(
            json.dumps([asdict(s) for s in structure.symbols], indent=2),
            encoding="utf-8",
        )

        edges_path = repo_dir / "edges.json"
        edges_path.write_text(
            json.dumps(
                {
                    "import_edges": [asdict(e) for e in structure.import_edges],
                    "call_edges": [asdict(e) for e in structure.call_edges],
                    "inherits_edges": [asdict(e) for e in structure.inherits_edges],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def load(self, repo_name: str) -> RepoStructure | None:
        if not self.has_repo(repo_name):
            return None

        repo_dir = self._repo_dir(repo_name)
        symbols_data = json.loads(
            (repo_dir / "symbols.json").read_text(encoding="utf-8")
        )
        edges_data = json.loads((repo_dir / "edges.json").read_text(encoding="utf-8"))

        return RepoStructure(
            symbols=[_symbol_from_dict(d) for d in symbols_data],
            import_edges=[ImportEdge(**d) for d in edges_data["import_edges"]],
            call_edges=[CallEdge(**d) for d in edges_data["call_edges"]],
            inherits_edges=[InheritsEdge(**d) for d in edges_data["inherits_edges"]],
        )

    def has_repo(self, repo_name: str) -> bool:
        repo_dir = self._repo_dir(repo_name)
        return (repo_dir / "symbols.json").exists() and (
            repo_dir / "edges.json"
        ).exists()

    def _repo_dir(self, repo_name: str) -> Path:
        return self._base_dir / repo_name


def _symbol_from_dict(data: dict) -> Symbol:
    return Symbol(**{**data, "decorators": tuple(data["decorators"])})
