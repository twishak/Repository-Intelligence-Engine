from codebase_agent.embeddings import CodeEmbedder
from codebase_agent.intelligence import RepoIntelligenceStore
from codebase_agent.intelligence.symbol_table import SymbolTable
from codebase_agent.knowledge.base import KnowledgeBase
from codebase_agent.knowledge.default import DefaultKnowledgeBase
from codebase_agent.knowledge.errors import (
    IncompatibleSchemaError,
    RepoNotIngestedError,
)
from codebase_agent.knowledge.files import FileSourceStore
from codebase_agent.knowledge.metadata import CURRENT_SCHEMA_VERSION, RepoMetadataStore
from codebase_agent.knowledge.snippets import SymbolSourceStore
from codebase_agent.storage import CodeVectorStore


class KnowledgeBaseFactory:
    """Builds a fully-wired KnowledgeBase for one repo from its persisted
    artifacts.

    Owns dependency construction (loading stores, wiring the embedder and
    vector store); `KnowledgeBaseRegistry` owns lifecycle/caching of the
    objects this produces. Kept separate so neither class does both jobs.
    """

    def __init__(
        self,
        embedder: CodeEmbedder | None = None,
        vector_store: CodeVectorStore | None = None,
        intelligence_store: RepoIntelligenceStore | None = None,
        source_store: SymbolSourceStore | None = None,
        file_source_store: FileSourceStore | None = None,
        metadata_store: RepoMetadataStore | None = None,
    ) -> None:
        self._embedder = embedder or CodeEmbedder()
        self._vector_store = vector_store or CodeVectorStore()
        self._intelligence_store = intelligence_store or RepoIntelligenceStore()
        self._source_store = source_store or SymbolSourceStore()
        self._file_source_store = file_source_store or FileSourceStore()
        self._metadata_store = metadata_store or RepoMetadataStore()

    def build(self, repo_name: str) -> KnowledgeBase:
        metadata = self._metadata_store.load(repo_name)
        if metadata is None:
            raise RepoNotIngestedError(repo_name)
        if metadata.schema_version != CURRENT_SCHEMA_VERSION:
            raise IncompatibleSchemaError(
                repo_name, metadata.schema_version, CURRENT_SCHEMA_VERSION
            )

        structure = self._intelligence_store.load(repo_name)
        if structure is None:
            raise RepoNotIngestedError(repo_name)

        return DefaultKnowledgeBase(
            repo_name=repo_name,
            symbol_table=SymbolTable.from_structure(structure),
            structure=structure,
            sources=self._source_store.load(repo_name),
            file_sources=self._file_source_store.load(repo_name),
            vector_store=self._vector_store,
            embedder=self._embedder,
            metadata=metadata,
            metadata_store=self._metadata_store,
        )

    def list_available_repos(self) -> list[str]:
        return self._metadata_store.list_repos()
