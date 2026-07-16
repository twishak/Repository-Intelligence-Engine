import logging
from collections import Counter
from datetime import datetime, timezone

from codebase_agent.application.errors import IngestionFailedError
from codebase_agent.chunking import chunk_source_files
from codebase_agent.embeddings import CodeEmbedder
from codebase_agent.ingestion import discover_files, get_repo_path
from codebase_agent.intelligence import (
    RepoIntelligenceStore,
    build_graph,
    extract_repo_structure,
)
from codebase_agent.knowledge import (
    FileSourceStore,
    KnowledgeBaseRegistry,
    RepoMetadata,
    RepoMetadataStore,
    SymbolSourceStore,
    build_file_sources,
    build_symbol_sources,
)
from codebase_agent.storage import CodeVectorStore

logger = logging.getLogger(__name__)


class IngestionService:
    """Ingests a repository (local path or git URL) end to end.

    Same steps as scripts/ingest_repo.py's main(), as a reusable, testable
    class - no new business logic, just a callable home for the existing
    orchestration so the CLI and API can both use it.
    """

    def __init__(
        self,
        embedder: CodeEmbedder | None = None,
        vector_store: CodeVectorStore | None = None,
        intelligence_store: RepoIntelligenceStore | None = None,
        source_store: SymbolSourceStore | None = None,
        file_source_store: FileSourceStore | None = None,
        metadata_store: RepoMetadataStore | None = None,
        kb_registry: KnowledgeBaseRegistry | None = None,
    ) -> None:
        self._embedder = embedder or CodeEmbedder()
        self._vector_store = vector_store or CodeVectorStore()
        self._intelligence_store = intelligence_store or RepoIntelligenceStore()
        self._source_store = source_store or SymbolSourceStore()
        self._file_source_store = file_source_store or FileSourceStore()
        self._metadata_store = metadata_store or RepoMetadataStore()
        self._kb_registry = kb_registry or KnowledgeBaseRegistry()

    def ingest_repository(self, source: str) -> RepoMetadata:
        try:
            repo_path = get_repo_path(source)
        except ValueError as e:
            raise IngestionFailedError(source, str(e)) from e

        repo_name = repo_path.name
        logger.info("Ingesting %s (repo: %s)", repo_path, repo_name)

        sources = discover_files(repo_path)
        if not sources:
            raise IngestionFailedError(source, "no in-scope files found")
        logger.info("Discovered %d file(s)", len(sources))

        chunks = chunk_source_files(sources)
        if not chunks:
            raise IngestionFailedError(source, "no chunks produced")
        logger.info(
            "Produced %d chunk(s): %s",
            len(chunks),
            dict(Counter(c.chunk_type for c in chunks)),
        )

        vectors = self._embedder.embed([c.content for c in chunks])
        self._vector_store.rebuild_repo_collection(repo_name, chunks, vectors)
        logger.info("Stored %d chunk(s) in collection '%s'", len(chunks), repo_name)

        structure = extract_repo_structure(sources)
        graph = build_graph(structure)
        self._intelligence_store.save(repo_name, structure)
        logger.info(
            "Extracted %d symbol(s), %d import edge(s), %d call edge(s), %d inheritance edge(s) "
            "(%d graph nodes, %d graph edges)",
            len(structure.symbols),
            len(structure.import_edges),
            len(structure.call_edges),
            len(structure.inherits_edges),
            graph.number_of_nodes(),
            graph.number_of_edges(),
        )

        self._source_store.save(repo_name, build_symbol_sources(structure, sources))
        self._file_source_store.save(repo_name, build_file_sources(sources))

        metadata = RepoMetadata(
            repo_name=repo_name,
            source=source,
            ingested_at=datetime.now(timezone.utc).isoformat(),
            files=tuple(s.path for s in sources),
            symbol_count=len(structure.symbols),
        )
        self._metadata_store.save(metadata)
        logger.info(
            "Saved knowledge-layer metadata for '%s' (schema v%d)",
            repo_name,
            metadata.schema_version,
        )

        # Drop any cached KnowledgeBase for this repo so a subsequent lookup
        # rebuilds from the freshly-ingested artifacts instead of serving a
        # stale pre-ingestion (or previous-version) instance.
        self._kb_registry.invalidate(repo_name)

        return metadata
