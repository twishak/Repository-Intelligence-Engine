from codebase_agent.application.services._kb_lookup import get_knowledge_base
from codebase_agent.knowledge import KnowledgeBaseRegistry, RepoMetadata


class RepositoryService:
    """Lists and looks up ingested repositories."""

    def __init__(self, kb_registry: KnowledgeBaseRegistry | None = None) -> None:
        self._kb_registry = kb_registry or KnowledgeBaseRegistry()

    def list_repositories(self) -> list[str]:
        return self._kb_registry.list_repos()

    def get_repository(self, repo_name: str) -> RepoMetadata:
        kb = get_knowledge_base(self._kb_registry, repo_name)
        return kb.get_metadata()

    def repository_exists(self, repo_name: str) -> bool:
        """Reusable existence check for the presentation layer - avoids every
        caller needing to catch RepositoryNotFoundError just to ask "is this
        repo there".
        """
        return repo_name in self.list_repositories()
