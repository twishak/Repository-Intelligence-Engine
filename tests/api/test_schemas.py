from codebase_agent.api.schemas import (
    AnswerResponse,
    RepositoryMetadataResponse,
    RepositoryReportResponse,
)
from codebase_agent.insights.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    RepositoryReport,
    RepositoryStatistics,
    make_finding_id,
)
from codebase_agent.knowledge import RepoMetadata
from codebase_agent.reasoning import AnswerConfidence, ReasoningResult
from codebase_agent.retrieval.evidence import EvidenceBundle
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)


def test_repository_metadata_response_from_domain():
    metadata = RepoMetadata(
        repo_name="repo",
        source="/x",
        ingested_at="t",
        files=("a.py", "b.py"),
        symbol_count=2,
    )

    response = RepositoryMetadataResponse.from_domain(metadata)

    assert response.repo_name == "repo"
    assert response.file_count == 2


def test_answer_response_from_domain():
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
    result = ReasoningResult(
        question="q",
        answer="a",
        confidence=AnswerConfidence.MEDIUM,
        evidence_sufficient=False,
        assumptions=("x",),
        limitations=("y",),
        citations=(),
        cited_evidence_indices=(),
        validation_issues=(),
        evidence_bundle=bundle,
        model="m",
        prompt_version="v1",
        reasoning_time_seconds=0.2,
    )

    response = AnswerResponse.from_domain(result)

    assert response.confidence == "medium"
    assert response.assumptions == ["x"]
    assert response.limitations == ["y"]


def test_repository_report_response_from_domain():
    finding = Finding(
        id=make_finding_id(FindingCategory.TODO, "a.py", "3"),
        category=FindingCategory.TODO,
        severity=FindingSeverity.INFO,
        title="t",
        description="d",
        qualified_name=None,
        file_path="a.py",
        start_line=3,
        end_line=3,
    )
    report = RepositoryReport(
        metadata=RepoMetadata(
            repo_name="repo", source="/x", ingested_at="t", files=(), symbol_count=0
        ),
        statistics=RepositoryStatistics(
            total_files=1,
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
        findings=(finding,),
        summary=None,
        generated_at="t",
        analyzers_run=("todo",),
        warnings=(),
        execution_time_seconds=0.05,
    )

    response = RepositoryReportResponse.from_domain(report)

    assert response.repo_name == "repo"
    assert response.statistics["total_files"] == 1
    assert response.finding_counts == {"todo": 1}
    assert len(response.findings) == 1
