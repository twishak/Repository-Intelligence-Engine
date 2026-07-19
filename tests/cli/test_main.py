from dataclasses import replace
from unittest.mock import patch

from typer.testing import CliRunner

from codebase_agent.application import ApplicationError
from codebase_agent.cli.main import app
from codebase_agent.insights import RepositoryReport, RepositoryStatistics
from codebase_agent.knowledge import RepoMetadata
from codebase_agent.reasoning import AnswerConfidence, Citation, ReasoningResult
from codebase_agent.retrieval.evidence import EvidenceBundle, EvidenceSource
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)

runner = CliRunner()


def _metadata(repo_name: str = "repo") -> RepoMetadata:
    return RepoMetadata(
        repo_name=repo_name,
        source="/x",
        ingested_at="t",
        files=("a.py", "b.py"),
        symbol_count=2,
    )


def _answer() -> ReasoningResult:
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH),)
    )
    bundle = EvidenceBundle(
        question="q",
        plan=plan,
        items=(),
        retrievers_used=(),
        warnings=(),
        execution_time_seconds=0.0,
    )
    return ReasoningResult(
        question="q",
        answer="the answer",
        confidence=AnswerConfidence.HIGH,
        evidence_sufficient=True,
        assumptions=(),
        limitations=(),
        citations=(),
        cited_evidence_indices=(),
        validation_issues=(),
        evidence_bundle=bundle,
        model="m",
        prompt_version="v1",
        reasoning_time_seconds=0.1,
    )


def _report(repo_name: str = "repo") -> RepositoryReport:
    return RepositoryReport(
        metadata=_metadata(repo_name),
        statistics=RepositoryStatistics(
            total_files=1,
            total_symbols=1,
            function_count=1,
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
        analyzers_run=("dead_code",),
        warnings=(),
        execution_time_seconds=0.01,
    )


@patch("codebase_agent.cli.main.IngestionService")
def test_ingest_command_prints_metadata(mock_service_cls):
    mock_service_cls.return_value.ingest_repository.return_value = _metadata()

    result = runner.invoke(app, ["ingest", "/path/to/repo"])

    assert result.exit_code == 0
    assert "repo" in result.output
    mock_service_cls.return_value.ingest_repository.assert_called_once_with(
        "/path/to/repo"
    )


@patch("codebase_agent.cli.main.IngestionService")
def test_ingest_command_reports_application_error(mock_service_cls):
    mock_service_cls.return_value.ingest_repository.side_effect = ApplicationError(
        "boom"
    )

    result = runner.invoke(app, ["ingest", "/bad/path"])

    assert result.exit_code == 1
    assert "boom" in result.output


@patch("codebase_agent.cli.main.RepositoryService")
def test_list_command_prints_repos(mock_service_cls):
    mock_service_cls.return_value.list_repositories.return_value = ["repo-a", "repo-b"]

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "repo-a" in result.output
    assert "repo-b" in result.output


@patch("codebase_agent.cli.main.RepositoryService")
def test_list_command_handles_empty(mock_service_cls):
    mock_service_cls.return_value.list_repositories.return_value = []

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No repositories" in result.output


@patch("codebase_agent.cli.main.RepositoryService")
def test_info_command_prints_metadata(mock_service_cls):
    mock_service_cls.return_value.get_repository.return_value = _metadata("myrepo")

    result = runner.invoke(app, ["info", "myrepo"])

    assert result.exit_code == 0
    assert "myrepo" in result.output


@patch("codebase_agent.cli.main.ReasoningService")
def test_ask_command_prints_answer(mock_service_cls):
    mock_service_cls.return_value.answer_question.return_value = _answer()

    result = runner.invoke(app, ["ask", "repo", "what does this do?"])

    assert result.exit_code == 0
    assert "the answer" in result.output


@patch("codebase_agent.cli.main.ReasoningService")
def test_ask_command_omits_none_none_for_file_level_citation(mock_service_cls):
    # Regression test: import_graph citations have no line numbers, and
    # rendering that as literal "path:None-None" reads as broken output.
    answer = replace(
        _answer(),
        citations=(
            Citation(
                evidence_index=1,
                qualified_name=None,
                file_path="pkg/a.py",
                start_line=None,
                end_line=None,
                source=EvidenceSource.IMPORT_GRAPH,
            ),
        ),
    )
    mock_service_cls.return_value.answer_question.return_value = answer

    result = runner.invoke(app, ["ask", "repo", "what imports a.py?"])

    assert result.exit_code == 0
    assert "None-None" not in result.output
    assert "pkg/a.py" in result.output


@patch("codebase_agent.cli.main.InsightsService")
def test_analyze_command_prints_report(mock_service_cls):
    mock_service_cls.return_value.analyze_repository.return_value = _report()

    result = runner.invoke(app, ["analyze", "repo"])

    assert result.exit_code == 0
    assert "Repository Report: repo" in result.output


def test_analyze_command_rejects_unknown_category():
    result = runner.invoke(app, ["analyze", "repo", "--category", "bogus"])

    assert result.exit_code == 1
    assert "Unknown category" in result.output
