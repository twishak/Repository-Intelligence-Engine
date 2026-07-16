from dataclasses import dataclass, field

# "function" | "method" | "class" | "module" - mirrors chunking.CodeChunk's
# chunk_type vocabulary where the concepts overlap, but this is a separate
# type: symbols describe structure, chunks describe retrievable text.
SymbolKind = str


@dataclass(frozen=True)
class Symbol:
    qualified_name: str
    kind: SymbolKind
    file_path: str
    start_line: int
    end_line: int
    signature: str
    docstring: str | None
    decorators: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImportEdge:
    importer_file: str
    imported_module: str
    # Repo-relative file path the import resolved to, or None if it points
    # outside the repo (stdlib, third-party, or unresolvable dynamic import).
    resolved_file: str | None


@dataclass(frozen=True)
class CallEdge:
    caller_qualified_name: str
    callee_name: str
    # Resolved qualified name of the callee, or None if it couldn't be
    # matched to a known repo symbol (external call, dynamic dispatch, etc.).
    callee_qualified_name: str | None
    file_path: str
    line: int


@dataclass(frozen=True)
class InheritsEdge:
    class_qualified_name: str
    base_name: str
    base_qualified_name: str | None


@dataclass(frozen=True)
class RepoStructure:
    """Everything extracted from a repo's source: the raw material for the
    symbol table and the graph, kept independent of how either is built.
    """

    symbols: list[Symbol] = field(default_factory=list)
    import_edges: list[ImportEdge] = field(default_factory=list)
    call_edges: list[CallEdge] = field(default_factory=list)
    inherits_edges: list[InheritsEdge] = field(default_factory=list)
