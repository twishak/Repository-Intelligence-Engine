import argparse
import logging
from collections import Counter
from datetime import datetime, timezone

from rich.logging import RichHandler

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
    RepoMetadata,
    RepoMetadataStore,
    SymbolSourceStore,
    build_file_sources,
    build_symbol_sources,
)
from codebase_agent.storage import CodeVectorStore

logger = logging.getLogger(__name__)


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(show_path=False)],
    )

    repo_path = get_repo_path(args.repo)
    repo_name = repo_path.name
    logger.info("Ingesting %s (collection: %s)", repo_path, repo_name)

    sources = discover_files(repo_path)
    logger.info("Discovered %d Python file(s)", len(sources))
    if not sources:
        logger.warning("No in-scope files found - nothing to ingest.")
        return

    chunks = chunk_source_files(sources)
    if not chunks:
        logger.warning("No chunks produced - nothing to embed.")
        return
    type_counts = Counter(c.chunk_type for c in chunks)
    logger.info("Produced %d chunk(s): %s", len(chunks), dict(type_counts))

    embedder = CodeEmbedder()
    vectors = embedder.embed([c.content for c in chunks])

    store = CodeVectorStore()
    store.rebuild_repo_collection(repo_name, chunks, vectors)
    logger.info("Stored %d chunk(s) in collection '%s'", len(chunks), repo_name)

    structure = extract_repo_structure(sources)
    graph = build_graph(structure)
    RepoIntelligenceStore().save(repo_name, structure)
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

    symbol_sources = build_symbol_sources(structure, sources)
    SymbolSourceStore().save(repo_name, symbol_sources)

    file_sources = build_file_sources(sources)
    FileSourceStore().save(repo_name, file_sources)

    metadata = RepoMetadata(
        repo_name=repo_name,
        source=args.repo,
        ingested_at=datetime.now(timezone.utc).isoformat(),
        files=tuple(s.path for s in sources),
        symbol_count=len(structure.symbols),
    )
    RepoMetadataStore().save(metadata)
    logger.info(
        "Saved knowledge-layer metadata for '%s' (schema v%d)",
        repo_name,
        metadata.schema_version,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a repository into the codebase-understanding-agent vector store."
    )
    parser.add_argument(
        "repo", help="Local path or git URL of the repository to ingest."
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
