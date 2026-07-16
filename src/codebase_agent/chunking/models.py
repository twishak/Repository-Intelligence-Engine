from dataclasses import dataclass


@dataclass(frozen=True)
class CodeChunk:
    id: str
    file_path: str
    chunk_type: str  # "function" | "method" | "class_skeleton" | "module"
    qualified_name: str
    start_line: int
    end_line: int
    content: str
    docstring: str | None
