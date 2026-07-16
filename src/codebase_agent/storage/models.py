from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    file_path: str
    chunk_type: str
    qualified_name: str
    start_line: int
    end_line: int
    content: str
    docstring: str | None
    # None for exact-match/lexical lookups, which aren't similarity-ranked.
    distance: float | None
