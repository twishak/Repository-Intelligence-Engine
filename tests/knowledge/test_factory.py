from pathlib import Path
from unittest.mock import Mock

import pytest

from codebase_agent.intelligence import RepoIntelligenceStore
from codebase_agent.intelligence.models import RepoStructure, Symbol
from codebase_agent.knowledge.errors import (
    IncompatibleSchemaError,
    RepoNotIngestedError,
)
from codebase_agent.knowledge.factory import KnowledgeBaseFactory
from codebase_agent.knowledge.metadata import (
    CURRENT_SCHEMA_VERSION,
    RepoMetadata,
    RepoMetadataStore,
)
from codebase_agent.knowledge.snippets import SymbolSourceStore


def _symbol(qualified_name: str = "pkg.a.foo") -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind="function",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        signature="...",
        docstring=None,
    )


def _factory(
    tmp_path: Path,
) -> tuple[
    KnowledgeBaseFactory, RepoMetadataStore, RepoIntelligenceStore, SymbolSourceStore
]:
    metadata_store = RepoMetadataStore(base_dir=tmp_path / "metadata")
    intelligence_store = RepoIntelligenceStore(base_dir=tmp_path / "graph")
    source_store = SymbolSourceStore(base_dir=tmp_path / "metadata")
    factory = KnowledgeBaseFactory(
        embedder=Mock(),
        vector_store=Mock(),
        intelligence_store=intelligence_store,
        source_store=source_store,
        metadata_store=metadata_store,
    )
    return factory, metadata_store, intelligence_store, source_store


def _ingest(
    metadata_store: RepoMetadataStore,
    intelligence_store: RepoIntelligenceStore,
    repo_name: str = "myrepo",
    schema_version: int = CURRENT_SCHEMA_VERSION,
) -> RepoStructure:
    structure = RepoStructure(symbols=[_symbol()])
    intelligence_store.save(repo_name, structure)
    metadata_store.save(
        RepoMetadata(
            repo_name=repo_name,
            source="/x",
            ingested_at="t",
            files=("pkg/a.py",),
            symbol_count=1,
            schema_version=schema_version,
        )
    )
    return structure


def test_build_returns_working_knowledge_base(tmp_path: Path):
    factory, metadata_store, intelligence_store, _ = _factory(tmp_path)
    _ingest(metadata_store, intelligence_store)

    kb = factory.build("myrepo")

    assert kb.get_symbol("pkg.a.foo") is not None
    assert kb.get_metadata().repo_name == "myrepo"


def test_build_raises_when_repo_never_ingested(tmp_path: Path):
    factory, _, _, _ = _factory(tmp_path)

    with pytest.raises(RepoNotIngestedError):
        factory.build("missing")


def test_build_raises_on_schema_mismatch(tmp_path: Path):
    factory, metadata_store, intelligence_store, _ = _factory(tmp_path)
    _ingest(
        metadata_store, intelligence_store, schema_version=CURRENT_SCHEMA_VERSION + 1
    )

    with pytest.raises(IncompatibleSchemaError):
        factory.build("myrepo")


def test_list_available_repos(tmp_path: Path):
    factory, metadata_store, intelligence_store, _ = _factory(tmp_path)
    _ingest(metadata_store, intelligence_store, repo_name="repo-a")
    _ingest(metadata_store, intelligence_store, repo_name="repo-b")

    assert factory.list_available_repos() == ["repo-a", "repo-b"]
