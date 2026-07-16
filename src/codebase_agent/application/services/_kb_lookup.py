from codebase_agent.application.errors import (
    RepositoryIncompatibleError,
    RepositoryNotFoundError,
)
from codebase_agent.knowledge import (
    IncompatibleSchemaError,
    KnowledgeBase,
    KnowledgeBaseRegistry,
    RepoNotIngestedError,
)


def get_knowledge_base(
    kb_registry: KnowledgeBaseRegistry, repo_name: str
) -> KnowledgeBase:
    """Look up a repo's KnowledgeBase, translating knowledge-layer errors into
    the application layer's own exception types - the one place that
    translation happens, shared by the services that need it.
    """
    try:
        return kb_registry.get(repo_name)
    except RepoNotIngestedError:
        raise RepositoryNotFoundError(repo_name) from None
    except IncompatibleSchemaError as e:
        raise RepositoryIncompatibleError(
            repo_name, e.found_version, e.expected_version
        ) from None
