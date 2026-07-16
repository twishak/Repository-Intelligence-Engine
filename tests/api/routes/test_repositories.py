from unittest.mock import Mock

from fastapi.testclient import TestClient

from codebase_agent.api.app import create_app
from codebase_agent.api.dependencies import (
    get_ingestion_service,
    get_repository_service,
)
from codebase_agent.application import IngestionFailedError, RepositoryNotFoundError
from codebase_agent.knowledge import RepoMetadata


def _metadata() -> RepoMetadata:
    return RepoMetadata(
        repo_name="repo", source="/x", ingested_at="t", files=("a.py",), symbol_count=1
    )


def test_list_repositories():
    app = create_app()
    service = Mock()
    service.list_repositories.return_value = ["repo-a", "repo-b"]
    app.dependency_overrides[get_repository_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/v1/repositories")

    assert response.status_code == 200
    assert response.json() == ["repo-a", "repo-b"]


def test_get_repository():
    app = create_app()
    service = Mock()
    service.get_repository.return_value = _metadata()
    app.dependency_overrides[get_repository_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/v1/repositories/repo")

    assert response.status_code == 200
    body = response.json()
    assert body["repo_name"] == "repo"
    assert body["file_count"] == 1


def test_get_repository_not_found():
    app = create_app()
    service = Mock()
    service.get_repository.side_effect = RepositoryNotFoundError("missing")
    app.dependency_overrides[get_repository_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/v1/repositories/missing")

    assert response.status_code == 404


def test_ingest_repository():
    app = create_app()
    service = Mock()
    service.ingest_repository.return_value = _metadata()
    app.dependency_overrides[get_ingestion_service] = lambda: service

    with TestClient(app) as client:
        response = client.post("/v1/repositories", json={"source": "/some/path"})

    assert response.status_code == 201
    service.ingest_repository.assert_called_once_with("/some/path")


def test_ingest_repository_failure():
    app = create_app()
    service = Mock()
    service.ingest_repository.side_effect = IngestionFailedError(
        "/bad", "no files found"
    )
    app.dependency_overrides[get_ingestion_service] = lambda: service

    with TestClient(app) as client:
        response = client.post("/v1/repositories", json={"source": "/bad"})

    assert response.status_code == 422
