from pathlib import Path
from unittest.mock import Mock

import pytest

from codebase_agent.application.errors import IngestionFailedError
from codebase_agent.application.services.ingestion_service import IngestionService


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _service(**overrides) -> IngestionService:
    defaults = dict(
        embedder=Mock(),
        vector_store=Mock(),
        intelligence_store=Mock(),
        source_store=Mock(),
        file_source_store=Mock(),
        metadata_store=Mock(),
        kb_registry=Mock(),
    )
    defaults["embedder"].embed.return_value = [[0.1, 0.2]]
    defaults.update(overrides)
    return IngestionService(**defaults)


def test_ingests_a_local_repo_and_returns_metadata(tmp_path: Path):
    repo_dir = tmp_path / "demo_repo"
    _write(repo_dir / "pkg" / "a.py", "def foo():\n    return 1\n")

    embedder = Mock()
    embedder.embed.return_value = [[0.1, 0.2]]
    vector_store = Mock()
    intelligence_store = Mock()
    source_store = Mock()
    file_source_store = Mock()
    metadata_store = Mock()
    kb_registry = Mock()

    service = IngestionService(
        embedder=embedder,
        vector_store=vector_store,
        intelligence_store=intelligence_store,
        source_store=source_store,
        file_source_store=file_source_store,
        metadata_store=metadata_store,
        kb_registry=kb_registry,
    )

    metadata = service.ingest_repository(str(repo_dir))

    assert metadata.repo_name == "demo_repo"
    assert metadata.source == str(repo_dir)
    assert metadata.files == ("pkg/a.py",)
    assert metadata.symbol_count == 1
    vector_store.rebuild_repo_collection.assert_called_once()
    intelligence_store.save.assert_called_once()
    source_store.save.assert_called_once()
    file_source_store.save.assert_called_once()
    metadata_store.save.assert_called_once_with(metadata)
    kb_registry.invalidate.assert_called_once_with("demo_repo")


def test_raises_ingestion_failed_for_nonexistent_path():
    service = _service()

    with pytest.raises(IngestionFailedError):
        service.ingest_repository("/definitely/does/not/exist")


def test_raises_ingestion_failed_when_no_in_scope_files(tmp_path: Path):
    repo_dir = tmp_path / "empty_repo"
    _write(repo_dir / "README.md", "no python here\n")

    service = _service()

    with pytest.raises(IngestionFailedError):
        service.ingest_repository(str(repo_dir))
