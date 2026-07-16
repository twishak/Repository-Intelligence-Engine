import dataclasses

from pydantic import BaseModel, ConfigDict

from codebase_agent import __version__
from codebase_agent.insights import Finding, RepositoryReport
from codebase_agent.knowledge import CURRENT_SCHEMA_VERSION, RepoMetadata
from codebase_agent.reasoning import Citation, ReasoningResult, ValidationIssue


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = __version__
    schema_version: int = CURRENT_SCHEMA_VERSION
    model: str


class IngestRepositoryRequest(BaseModel):
    source: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"source": "https://github.com/psf/requests.git"},
                {"source": "/home/user/projects/my-repo"},
            ]
        }
    )


class RepositoryMetadataResponse(BaseModel):
    repo_name: str
    source: str
    ingested_at: str
    file_count: int
    symbol_count: int
    schema_version: int
    summary: str | None

    @classmethod
    def from_domain(cls, metadata: RepoMetadata) -> "RepositoryMetadataResponse":
        return cls(
            repo_name=metadata.repo_name,
            source=metadata.source,
            ingested_at=metadata.ingested_at,
            file_count=len(metadata.files),
            symbol_count=metadata.symbol_count,
            schema_version=metadata.schema_version,
            summary=metadata.summary,
        )


class AskQuestionRequest(BaseModel):
    question: str
    active_file: str | None = None
    active_symbol: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"question": "Where is authentication handled?"},
                {
                    "question": "What would break if I changed this?",
                    "active_file": "src/codebase_agent/knowledge/default.py",
                    "active_symbol": "DefaultKnowledgeBase.get_symbol",
                },
            ]
        }
    )


class CitationResponse(BaseModel):
    evidence_index: int
    qualified_name: str | None
    file_path: str | None
    start_line: int | None
    end_line: int | None
    source: str

    @classmethod
    def from_domain(cls, citation: Citation) -> "CitationResponse":
        return cls(
            evidence_index=citation.evidence_index,
            qualified_name=citation.qualified_name,
            file_path=citation.file_path,
            start_line=citation.start_line,
            end_line=citation.end_line,
            source=citation.source.value,
        )


class ValidationIssueResponse(BaseModel):
    severity: str
    message: str

    @classmethod
    def from_domain(cls, issue: ValidationIssue) -> "ValidationIssueResponse":
        return cls(severity=issue.severity.value, message=issue.message)


class AnswerResponse(BaseModel):
    question: str
    answer: str
    confidence: str
    evidence_sufficient: bool
    assumptions: list[str]
    limitations: list[str]
    citations: list[CitationResponse]
    validation_issues: list[ValidationIssueResponse]
    model: str
    prompt_version: str

    @classmethod
    def from_domain(cls, result: ReasoningResult) -> "AnswerResponse":
        return cls(
            question=result.question,
            answer=result.answer,
            confidence=result.confidence.value,
            evidence_sufficient=result.evidence_sufficient,
            assumptions=list(result.assumptions),
            limitations=list(result.limitations),
            citations=[CitationResponse.from_domain(c) for c in result.citations],
            validation_issues=[
                ValidationIssueResponse.from_domain(i) for i in result.validation_issues
            ],
            model=result.model,
            prompt_version=result.prompt_version,
        )


class FindingResponse(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    description: str
    qualified_name: str | None
    file_path: str | None
    start_line: int | None
    end_line: int | None
    details: dict[str, str | int | float | bool]

    @classmethod
    def from_domain(cls, finding: Finding) -> "FindingResponse":
        return cls(
            id=finding.id,
            category=finding.category.value,
            severity=finding.severity.value,
            title=finding.title,
            description=finding.description,
            qualified_name=finding.qualified_name,
            file_path=finding.file_path,
            start_line=finding.start_line,
            end_line=finding.end_line,
            details=finding.details,
        )


class RepositoryReportResponse(BaseModel):
    repo_name: str
    generated_at: str
    statistics: dict[str, int]
    findings: list[FindingResponse]
    finding_counts: dict[str, int]
    warnings: list[str]
    execution_time_seconds: float

    @classmethod
    def from_domain(cls, report: RepositoryReport) -> "RepositoryReportResponse":
        return cls(
            repo_name=report.metadata.repo_name,
            generated_at=report.generated_at,
            statistics=dataclasses.asdict(report.statistics),
            findings=[FindingResponse.from_domain(f) for f in report.findings],
            finding_counts={c.value: n for c, n in report.finding_counts().items()},
            warnings=[f"[{w.analyzer}] {w.message}" for w in report.warnings],
            execution_time_seconds=report.execution_time_seconds,
        )
