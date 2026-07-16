import json
from dataclasses import asdict, dataclass
from pathlib import Path

from codebase_agent.config import settings

# Bump whenever a change to the ingestion pipeline (extraction logic, model
# shapes, persisted artifact formats) could make previously-ingested repos'
# artifacts incompatible with the current code. KnowledgeBaseFactory checks
# this and asks for re-ingestion rather than failing unpredictably.
CURRENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RepoMetadata:
    repo_name: str
    source: str  # local path or git URL passed to scripts/ingest_repo.py
    ingested_at: str  # ISO 8601 timestamp
    files: tuple[str, ...]  # repo-relative paths of every ingested source file
    symbol_count: int
    schema_version: int = CURRENT_SCHEMA_VERSION
    summary: str | None = None


class RepoMetadataStore:
    """Persists RepoMetadata as JSON, one directory per repo. Also the
    authoritative record of "which repos has this system ingested" - see
    `list_repos`.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or settings.knowledge_dir

    def save(self, metadata: RepoMetadata) -> None:
        repo_dir = self._repo_dir(metadata.repo_name)
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "metadata.json").write_text(
            json.dumps(asdict(metadata), indent=2), encoding="utf-8"
        )

    def load(self, repo_name: str) -> RepoMetadata | None:
        path = self._repo_dir(repo_name) / "metadata.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return RepoMetadata(**{**data, "files": tuple(data["files"])})

    def has_repo(self, repo_name: str) -> bool:
        return (self._repo_dir(repo_name) / "metadata.json").exists()

    def list_repos(self) -> list[str]:
        if not self._base_dir.exists():
            return []
        return sorted(p.parent.name for p in self._base_dir.glob("*/metadata.json"))

    def _repo_dir(self, repo_name: str) -> Path:
        return self._base_dir / repo_name
