import re
from pathlib import Path

from git import Repo

from codebase_agent.config import settings


def get_repo_path(source: str) -> Path:
    """Resolve `source` to a local directory, cloning it first if it's a git URL."""
    if _looks_like_git_url(source):
        dest = settings.repos_dir / _repo_name_from_url(source)
        if not dest.exists():
            Repo.clone_from(source, dest)
        return dest

    path = Path(source).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    return path


def _looks_like_git_url(source: str) -> bool:
    return source.startswith(("http://", "https://", "git@")) or source.endswith(".git")


def _repo_name_from_url(url: str) -> str:
    name = url.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"\.git$", "", name)
