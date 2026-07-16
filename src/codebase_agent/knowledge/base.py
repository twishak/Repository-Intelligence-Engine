from typing import Protocol, runtime_checkable

from codebase_agent.intelligence.models import (
    CallEdge,
    ImportEdge,
    InheritsEdge,
    Symbol,
)
from codebase_agent.knowledge.metadata import RepoMetadata
from codebase_agent.storage.models import RetrievedChunk


@runtime_checkable
class KnowledgeBase(Protocol):
    """Unified read/write access to everything known about one ingested repo.

    Every higher-level subsystem (retrieval, the agent, developer insights,
    the CLI, the future REST API) depends on this interface only - never on
    Chroma, NetworkX, or the on-disk JSON artifacts directly. That boundary
    is what lets the storage behind any of this change without callers
    changing too.

    Deliberately atomic: no ranking, no multi-hop composition, no "answer
    this question" method. Those are Retrieval/Agent concerns, built by
    combining these primitives - not by growing this interface. The same
    goes for the `all_*`/`get_file_source` whole-repo primitives added for
    repository analysis: generic enumeration, not analyzer-specific methods
    like `find_dead_code()` - an analysis subsystem is expected to build its
    own logic over these, the same way Retrieval builds strategies over the
    per-symbol lookups above.
    """

    def get_symbol(self, qualified_name: str) -> Symbol | None: ...

    def find_symbols_by_name(self, short_name: str) -> list[Symbol]:
        """All symbols whose qualified name ends in `short_name` - may return
        multiple matches (e.g. every class defining a `run` method)."""
        ...

    def symbols_in_file(self, file_path: str) -> list[Symbol]: ...

    def list_files(self) -> list[str]:
        """Repo-relative paths of every ingested source file."""
        ...

    def resolve_module(self, module_name: str) -> str | None:
        """Dotted module name (e.g. "pkg.sub") -> the file it resolves to,
        or None if it isn't a repo-local module."""
        ...

    def callers_of(self, qualified_name: str) -> list[CallEdge]:
        """Edges where this symbol is the callee. callee_qualified_name on
        each edge equals `qualified_name`; caller_qualified_name is who's
        calling it."""
        ...

    def callees_of(self, qualified_name: str) -> list[CallEdge]:
        """Edges where this symbol is the caller. Includes edges whose
        callee_qualified_name is None - a call this system couldn't resolve
        to a known symbol (external or dynamic), not one that was dropped."""
        ...

    def imports_of(self, file_path: str) -> list[ImportEdge]:
        """What this file imports."""
        ...

    def importers_of(self, file_path: str) -> list[ImportEdge]:
        """What imports this file."""
        ...

    def base_classes_of(self, qualified_name: str) -> list[InheritsEdge]: ...

    def subclasses_of(self, qualified_name: str) -> list[InheritsEdge]: ...

    def get_source(self, qualified_name: str) -> str | None:
        """Exact source text for a symbol, or None if unknown."""
        ...

    def get_file_source(self, file_path: str) -> str | None:
        """Full text of a file, or None if unknown. Covers text outside any
        symbol's bounds (module-level comments, blank lines between
        functions) - use this for whole-file scans; use `get_source` for a
        single symbol's exact text."""
        ...

    def all_symbols(self) -> list[Symbol]:
        """Every symbol in the repo. A generic whole-repo primitive - e.g.
        for a repository-analysis subsystem to build its own view over, not
        a substitute for adding analysis-specific methods here."""
        ...

    def all_import_edges(self) -> list[ImportEdge]:
        """Every import edge in the repo."""
        ...

    def all_call_edges(self) -> list[CallEdge]:
        """Every call edge in the repo."""
        ...

    def all_inherits_edges(self) -> list[InheritsEdge]:
        """Every inheritance edge in the repo."""
        ...

    def semantic_search(self, query: str, k: int = 8) -> list[RetrievedChunk]:
        """Embedding similarity search over the repo's indexed chunks."""
        ...

    def get_metadata(self) -> RepoMetadata: ...

    def set_summary(self, summary: str) -> None:
        """Persist a repo-level summary. Generating the summary text is a
        Developer Insights concern - this only stores it."""
        ...
