from pathlib import Path

from codebase_agent.knowledge.metadata import (
    CURRENT_SCHEMA_VERSION,
    RepoMetadata,
    RepoMetadataStore,
)


def _metadata(repo_name: str = "myrepo") -> RepoMetadata:
    return RepoMetadata(
        repo_name=repo_name,
        source="/local/path",
        ingested_at="2026-01-01T00:00:00+00:00",
        files=("pkg/a.py", "pkg/b.py"),
        symbol_count=5,
    )


def test_save_then_load_round_trips(tmp_path: Path):
    store = RepoMetadataStore(base_dir=tmp_path)
    metadata = _metadata()

    store.save(metadata)
    loaded = store.load("myrepo")

    assert loaded == metadata
    assert loaded.files == ("pkg/a.py", "pkg/b.py")


def test_defaults_schema_version_to_current():
    assert _metadata().schema_version == CURRENT_SCHEMA_VERSION


def test_has_repo(tmp_path: Path):
    store = RepoMetadataStore(base_dir=tmp_path)

    assert store.has_repo("myrepo") is False
    store.save(_metadata())
    assert store.has_repo("myrepo") is True


def test_load_missing_repo_returns_none(tmp_path: Path):
    store = RepoMetadataStore(base_dir=tmp_path)

    assert store.load("missing") is None


def test_list_repos(tmp_path: Path):
    store = RepoMetadataStore(base_dir=tmp_path)
    store.save(_metadata("repo-a"))
    store.save(_metadata("repo-b"))

    assert store.list_repos() == ["repo-a", "repo-b"]


def test_list_repos_empty_when_dir_missing(tmp_path: Path):
    store = RepoMetadataStore(base_dir=tmp_path / "does-not-exist")

    assert store.list_repos() == []
