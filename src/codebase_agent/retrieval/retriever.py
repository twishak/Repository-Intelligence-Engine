from codebase_agent.embeddings import CodeEmbedder
from codebase_agent.storage import CodeVectorStore, RetrievedChunk


class CodeRetriever:
    """Composable retrieval primitives over one repo's collection.

    Deciding which of these to call for a given question, and how to combine
    results, is the graph layer's job - this class only exposes the tools.
    """

    def __init__(
        self, embedder: CodeEmbedder | None = None, store: CodeVectorStore | None = None
    ) -> None:
        self._embedder = embedder or CodeEmbedder()
        self._store = store or CodeVectorStore()

    def semantic_search(
        self, repo_name: str, question: str, k: int = 8
    ) -> list[RetrievedChunk]:
        """Best for open-ended/conceptual questions, e.g. 'where is X handled'."""
        [query_vector] = self._embedder.embed([question])
        return self._store.query(repo_name, query_vector, n_results=k)

    def find_by_qualified_name(
        self, repo_name: str, name: str, k: int = 8
    ) -> list[RetrievedChunk]:
        """Best when the exact symbol is already known, e.g. 'explain what X does'."""
        return self._store.get_by_qualified_name(repo_name, name, n_results=k)

    def find_references(
        self, repo_name: str, identifier: str, k: int = 8
    ) -> list[RetrievedChunk]:
        """Lexical containment search approximating 'who calls/uses this', for
        'what would break if I changed Y' questions. Misses aliased imports,
        indirect calls, and polymorphic dispatch - see design notes.
        """
        return self._store.search_document_text(repo_name, identifier, n_results=k)
