import logging
import time
from datetime import datetime, timezone
from typing import Protocol

from codebase_agent.insights.analyzers import (
    ArchitectureAnalyzer,
    CircularDependencyAnalyzer,
    ComplexityAnalyzer,
    DeadCodeAnalyzer,
    TodoAnalyzer,
)
from codebase_agent.insights.models import AnalyzerWarning, Finding, RepositoryReport
from codebase_agent.insights.statistics import compute_statistics
from codebase_agent.knowledge import KnowledgeBase

logger = logging.getLogger(__name__)


class Analyzer(Protocol):
    name: str

    def analyze(self, kb: KnowledgeBase) -> list[Finding]: ...


def _default_analyzers() -> list[Analyzer]:
    return [
        DeadCodeAnalyzer(),
        CircularDependencyAnalyzer(),
        ComplexityAnalyzer(),
        TodoAnalyzer(),
        ArchitectureAnalyzer(),
    ]


class AnalysisRunner:
    """Runs a set of independent analyzers over one repo and aggregates
    their findings into a RepositoryReport.

    Analyzers never call each other or see each other's output - this class
    is the only place results are combined. One analyzer failing is recorded
    as a warning and skipped, not fatal to the run, mirroring
    RetrievalExecutor's per-step degradation in the retrieval engine.
    """

    def __init__(self, analyzers: list[Analyzer] | None = None) -> None:
        self._analyzers = analyzers if analyzers is not None else _default_analyzers()

    def run(self, kb: KnowledgeBase) -> RepositoryReport:
        start = time.perf_counter()
        findings: list[Finding] = []
        analyzers_run: list[str] = []
        warnings: list[AnalyzerWarning] = []

        for analyzer in self._analyzers:
            try:
                findings.extend(analyzer.analyze(kb))
                analyzers_run.append(analyzer.name)
            except Exception as e:
                logger.exception("Analyzer %s failed", analyzer.name)
                warnings.append(AnalyzerWarning(analyzer=analyzer.name, message=str(e)))

        return RepositoryReport(
            metadata=kb.get_metadata(),
            statistics=compute_statistics(kb),
            findings=tuple(findings),
            summary=None,
            generated_at=datetime.now(timezone.utc).isoformat(),
            analyzers_run=tuple(analyzers_run),
            warnings=tuple(warnings),
            execution_time_seconds=time.perf_counter() - start,
        )
