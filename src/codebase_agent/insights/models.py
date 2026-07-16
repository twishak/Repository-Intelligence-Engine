import hashlib
from dataclasses import dataclass, field
from enum import Enum

from codebase_agent.knowledge import RepoMetadata


class FindingCategory(str, Enum):
    DEAD_CODE = "dead_code"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    COMPLEXITY = "complexity"
    TODO = "todo"
    ARCHITECTURE = "architecture"


class FindingSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


def make_finding_id(category: FindingCategory, *parts: str) -> str:
    """Deterministic id for a finding: the same underlying issue gets the
    same id across re-analysis runs (a hash of category + locating parts,
    e.g. qualified_name/file_path/line), so a future UI can diff reports or
    track acknowledged findings instead of treating every run as all-new.
    """
    raw = "|".join((category.value, *(p for p in parts if p)))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class Finding:
    """One normalized analysis result, regardless of which analyzer produced
    it - the same 'normalize at the boundary' approach used for EvidenceItem
    in the retrieval engine. `details` holds the handful of analyzer-specific
    numbers (a complexity score, a cycle length) that don't merit a
    first-class field.
    """

    id: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    description: str
    qualified_name: str | None
    file_path: str | None
    start_line: int | None
    end_line: int | None
    details: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalyzerWarning:
    analyzer: str
    message: str


@dataclass(frozen=True)
class RepositoryStatistics:
    """Generic, analyzer-independent facts about the repo, derived directly
    from KnowledgeBase's whole-repo primitives - not from any analyzer's
    findings.
    """

    total_files: int
    total_symbols: int
    function_count: int
    method_count: int
    class_count: int
    total_import_edges: int
    total_call_edges: int
    total_inherits_edges: int
    resolved_call_edges: int
    resolved_import_edges: int


@dataclass(frozen=True)
class RepositoryReport:
    """The canonical output of the analysis subsystem - what the CLI, REST
    API, Markdown/JSON exporters, and any future UI consume.
    """

    metadata: RepoMetadata
    statistics: RepositoryStatistics
    findings: tuple[Finding, ...]
    # Placeholder for a future LLM-generated repository summary, built on top
    # of this report rather than replacing it - not populated by this
    # (deterministic, LLM-free) subsystem.
    summary: str | None
    generated_at: str
    analyzers_run: tuple[str, ...]
    warnings: tuple[AnalyzerWarning, ...]
    execution_time_seconds: float

    def by_category(self, category: FindingCategory) -> list[Finding]:
        return [f for f in self.findings if f.category == category]

    def by_severity(self, severity: FindingSeverity) -> list[Finding]:
        return [f for f in self.findings if f.severity == severity]

    def finding_counts(self) -> dict[FindingCategory, int]:
        counts: dict[FindingCategory, int] = {}
        for finding in self.findings:
            counts[finding.category] = counts.get(finding.category, 0) + 1
        return counts

    def is_empty(self) -> bool:
        return len(self.findings) == 0

    def __len__(self) -> int:
        return len(self.findings)

    def __iter__(self):
        return iter(self.findings)
