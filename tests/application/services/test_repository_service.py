from unittest.mock import Mock

import pytest

from codebase_agent.application.errors import RepositoryNotFoundError
from codebase_agent.application.services.repository_service import RepositoryService
from codebase_agent.knowledge import RepoMetadata, RepoNotIngestedError


def test_list_repositories_delegates_to_registry():
    kb_registry = Mock()
    kb_registry.list_repos.return_value = ["repo-a", "repo-b"]

    service = RepositoryService(kb_registry=kb_registry)

    assert service.list_repositories() == ["repo-a", "repo-b"]


def test_get_repository_returns_metadata():
    metadata = RepoMetadata(
        repo_name="repo", source="/x", ingested_at="t", files=(), symbol_count=0
    )
    kb = Mock()
    kb.get_metadata.return_value = metadata
    kb_registry = Mock()
    kb_registry.get.return_value = kb

    service = RepositoryService(kb_registry=kb_registry)

    assert service.get_repository("repo") == metadata


def test_get_repository_raises_not_found():
    kb_registry = Mock()
    kb_registry.get.side_effect = RepoNotIngestedError("repo")

    service = RepositoryService(kb_registry=kb_registry)

    with pytest.raises(RepositoryNotFoundError):
        service.get_repository("repo")


def test_repository_exists_true_and_false():
    kb_registry = Mock()
    kb_registry.list_repos.return_value = ["repo-a"]

    service = RepositoryService(kb_registry=kb_registry)

    assert service.repository_exists("repo-a") is True
    assert service.repository_exists("repo-b") is False
