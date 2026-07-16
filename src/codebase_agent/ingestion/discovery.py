import subprocess
from pathlib import Path

from codebase_agent.config import settings
from codebase_agent.ingestion.models import SourceFile

_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def discover_files(repo_path: Path) -> list[SourceFile]:
    """Find in-scope source files under `repo_path` and read their contents."""
    rel_paths = _list_git_tracked_files(repo_path)
    if rel_paths is None:
        rel_paths = _walk_files(repo_path)

    sources = []
    for rel_path in rel_paths:
        if not rel_path.endswith(settings.allowed_extensions):
            continue
        source = _read_source_file(repo_path, repo_path / rel_path)
        if source is not None:
            sources.append(source)
    return sources


def _list_git_tracked_files(repo_path: Path) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [line for line in result.stdout.splitlines() if line]


def _walk_files(repo_path: Path) -> list[str]:
    rel_paths = []
    for path in repo_path.rglob("*"):
        if path.is_dir():
            continue
        if any(part in _IGNORED_DIRS for part in path.relative_to(repo_path).parts):
            continue
        rel_paths.append(path.relative_to(repo_path).as_posix())
    return rel_paths


def _read_source_file(repo_path: Path, abs_path: Path) -> SourceFile | None:
    try:
        size = abs_path.stat().st_size
    except OSError:
        return None
    if size == 0 or size > settings.max_file_size_bytes:
        return None

    try:
        content = abs_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    # Some binary content still decodes as valid UTF-8 (e.g. embedded nulls in
    # otherwise-ASCII data), so the decode succeeding above isn't sufficient
    # on its own to prove this is a real source file.
    if "\x00" in content:
        return None

    return SourceFile(
        path=abs_path.relative_to(repo_path).as_posix(),
        absolute_path=str(abs_path),
        language="python",
        content=content,
        line_count=len(content.splitlines()),
    )
