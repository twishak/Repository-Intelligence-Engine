from codebase_agent.intelligence.models import RepoStructure, Symbol


class SymbolTable:
    """O(1) lookup over a repo's extracted symbols, indexed three ways."""

    def __init__(self, symbols: list[Symbol]) -> None:
        self._by_qualified_name: dict[str, Symbol] = {}
        self._by_file: dict[str, list[Symbol]] = {}
        self._by_short_name: dict[str, list[Symbol]] = {}

        for symbol in symbols:
            self._by_qualified_name[symbol.qualified_name] = symbol
            self._by_file.setdefault(symbol.file_path, []).append(symbol)
            short_name = symbol.qualified_name.rsplit(".", 1)[-1]
            self._by_short_name.setdefault(short_name, []).append(symbol)

    @classmethod
    def from_structure(cls, structure: RepoStructure) -> "SymbolTable":
        return cls(structure.symbols)

    def get(self, qualified_name: str) -> Symbol | None:
        return self._by_qualified_name.get(qualified_name)

    def symbols_in_file(self, file_path: str) -> list[Symbol]:
        return list(self._by_file.get(file_path, []))

    def find_by_short_name(self, short_name: str) -> list[Symbol]:
        """All symbols whose qualified name ends in `short_name` (e.g. the
        method name without its class prefix). May return multiple matches.
        """
        return list(self._by_short_name.get(short_name, []))

    def __len__(self) -> int:
        return len(self._by_qualified_name)

    def __iter__(self):
        return iter(self._by_qualified_name.values())
