from codebase_agent.knowledge.base import KnowledgeBase
from codebase_agent.knowledge.factory import KnowledgeBaseFactory


class KnowledgeBaseRegistry:
    """Lifecycle and caching for per-repo KnowledgeBase instances.

    Building one isn't free (loads the symbol table and structural edges
    from disk), so repeated lookups of the same repo return the same
    instance instead of rebuilding it. Construction itself belongs to
    `KnowledgeBaseFactory` - this class only manages lifecycle.
    """

    def __init__(self, factory: KnowledgeBaseFactory | None = None) -> None:
        self._factory = factory or KnowledgeBaseFactory()
        self._cache: dict[str, KnowledgeBase] = {}

    def get(self, repo_name: str) -> KnowledgeBase:
        if repo_name not in self._cache:
            self._cache[repo_name] = self._factory.build(repo_name)
        return self._cache[repo_name]

    def invalidate(self, repo_name: str) -> None:
        """Drop the cached instance, e.g. after re-ingesting the repo."""
        self._cache.pop(repo_name, None)

    def list_repos(self) -> list[str]:
        return self._factory.list_available_repos()
