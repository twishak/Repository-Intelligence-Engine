from unittest.mock import Mock

from fastapi.testclient import TestClient

from codebase_agent.api.app import create_app
from codebase_agent.api.dependencies import get_repository_service
from codebase_agent.application import RepositoryNotFoundError


def test_health_endpoint_reports_version_schema_and_model():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "schema_version" in body
    assert "model" in body


def test_response_includes_request_id_header():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/v1/health")

    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_each_request_gets_a_distinct_request_id():
    app = create_app()
    with TestClient(app) as client:
        first = client.get("/v1/health")
        second = client.get("/v1/health")

    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_application_error_maps_to_expected_status_and_body():
    app = create_app()
    service = Mock()
    service.get_repository.side_effect = RepositoryNotFoundError("missing-repo")
    app.dependency_overrides[get_repository_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/v1/repositories/missing-repo")

    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "RepositoryNotFoundError"
    assert "missing-repo" in body["message"]
    assert "request_id" in body
