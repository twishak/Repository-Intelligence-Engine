from dataclasses import replace

from codebase_agent.embeddings import CodeEmbedder
from codebase_agent.intelligence.models import (
    CallEdge,
    ImportEdge,
    InheritsEdge,
    RepoStructure,
    Symbol,
)
from codebase_agent.intelligence.symbol_table import SymbolTable
from codebase_agent.knowledge.metadata import RepoMetadata, RepoMetadataStore
from codebase_agent.storage import CodeVectorStore
from codebase_agent.storage.models import RetrievedChunk


class DefaultKnowledgeBase:
    """Default `KnowledgeBase` implementation: composes the Repository
    Intelligence artifacts (symbol table, structural edges), persisted
    source snippets, the vector store, and repo metadata for one repo.

    Relationship queries (`callers_of`, `imports_of`, etc.) filter the flat
    edge lists directly rather than walking a graph structure - at portfolio
    scale that's a handful of list comprehensions, fast enough, and avoids
    keeping a second derived representation in sync with the first.
    """

    def __init__(
        self,
        repo_name: str,
        symbol_table: SymbolTable,
        structure: RepoStructure,
        sources: dict[str, str],
        file_sources: dict[str, str],
        vector_store: CodeVectorStore,
        embedder: CodeEmbedder,
        metadata: RepoMetadata,
        metadata_store: RepoMetadataStore,
    ) -> None:
        self._repo_name = repo_name
        self._symbol_table = symbol_table
        self._structure = structure
        self._sources = sources
        self._file_sources = file_sources
        self._vector_store = vector_store
        self._embedder = embedder
        self._metadata = metadata
        self._metadata_store = metadata_store

    def get_symbol(self, qualified_name: str) -> Symbol | None:
        return self._symbol_table.get(qualified_name)

    def find_symbols_by_name(self, short_name: str) -> list[Symbol]:
        return self._symbol_table.find_by_short_name(short_name)

    def symbols_in_file(self, file_path: str) -> list[Symbol]:
        return self._symbol_table.symbols_in_file(file_path)

    def list_files(self) -> list[str]:
        return list(self._metadata.files)

    def resolve_module(self, module_name: str) -> str | None:
        for file_path in self._metadata.files:
            if _module_name_for_path(file_path) == module_name:
                return file_path
        return None

    def callers_of(self, qualified_name: str) -> list[CallEdge]:
        return [
            e
            for e in self._structure.call_edges
            if e.callee_qualified_name == qualified_name
        ]

    def callees_of(self, qualified_name: str) -> list[CallEdge]:
        return [
            e
            for e in self._structure.call_edges
            if e.caller_qualified_name == qualified_name
        ]

    def imports_of(self, file_path: str) -> list[ImportEdge]:
        return [e for e in self._structure.import_edges if e.importer_file == file_path]

    def importers_of(self, file_path: str) -> list[ImportEdge]:
        return [e for e in self._structure.import_edges if e.resolved_file == file_path]

    def base_classes_of(self, qualified_name: str) -> list[InheritsEdge]:
        return [
            e
            for e in self._structure.inherits_edges
            if e.class_qualified_name == qualified_name
        ]

    def subclasses_of(self, qualified_name: str) -> list[InheritsEdge]:
        return [
            e
            for e in self._structure.inherits_edges
            if e.base_qualified_name == qualified_name
        ]

    def get_source(self, qualified_name: str) -> str | None:
        return self._sources.get(qualified_name)

    def get_file_source(self, file_path: str) -> str | None:
        return self._file_sources.get(file_path)

    def all_symbols(self) -> list[Symbol]:
        return list(self._structure.symbols)

    def all_import_edges(self) -> list[ImportEdge]:
        return list(self._structure.import_edges)

    def all_call_edges(self) -> list[CallEdge]:
        return list(self._structure.call_edges)

    def all_inherits_edges(self) -> list[InheritsEdge]:
        return list(self._structure.inherits_edges)

    def semantic_search(self, query: str, k: int = 8) -> list[RetrievedChunk]:
        [query_vector] = self._embedder.embed([query])
        return self._vector_store.query(self._repo_name, query_vector, n_results=k)

    def get_metadata(self) -> RepoMetadata:
        return self._metadata

    def set_summary(self, summary: str) -> None:
        self._metadata = replace(self._metadata, summary=summary)
        self._metadata_store.save(self._metadata)


def _module_name_for_path(path: str) -> str:
    # Mirrors intelligence.python_extractor's derivation exactly (same pure
    # function of the path string, including the src-layout special case) so
    # resolve_module agrees with how import edges were resolved at
    # extraction time. Duplicated rather than imported to keep the knowledge
    # layer from depending on extraction internals - it's a handful of lines
    # of pure string logic.
    stem = path[:-3] if path.endswith(".py") else path
    parts = stem.split("/")
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)
