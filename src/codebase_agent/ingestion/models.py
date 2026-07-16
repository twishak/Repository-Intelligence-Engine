from dataclasses import dataclass


@dataclass(frozen=True)
class SourceFile:
    path: str  # relative to repo root, posix-style
    absolute_path: str
    language: str
    content: str
    line_count: int
