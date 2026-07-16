from unittest.mock import Mock

from fastapi.testclient import TestClient

from codebase_agent.api.app import create_app
from codebase_agent.api.dependencies import get_insights_service
from codebase_agent.insights import RepositoryReport, RepositoryStatistics
from codebase_agent.knowledge import RepoMetadata


def _report() -> RepositoryReport:
    return RepositoryReport(
        metadata=RepoMetadata(
            repo_name="repo", source="/x", ingested_at="t", files=(), symbol_count=0
        ),
        statistics=RepositoryStatistics(
            total_files=0,
            total_symbols=0,
            function_count=0,
            method_count=0,
            class_count=0,
            total_import_edges=0,
            total_call_edges=0,
            total_inherits_edges=0,
            resolved_call_edges=0,
            resolved_import_edges=0,
        ),
        findings=(),
        summary=None,
        generated_at="t",
        analyzers_run=(),
        warnings=(),
        execution_time_seconds=0.0,
    )


def test_analyze_repository():
    app = create_app()
    service = Mock()
    service.analyze_repository.return_value = _report()
    app.dependency_overrides[get_insights_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/v1/repositories/repo/insights")

    assert response.status_code == 200
    body = response.json()
    assert body["repo_name"] == "repo"
