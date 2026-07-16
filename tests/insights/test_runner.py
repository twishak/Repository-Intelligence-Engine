from unittest.mock import Mock

from codebase_agent.insights.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    RepositoryStatistics,
)
from codebase_agent.insights.runner import AnalysisRunner
from codebase_agent.knowledge import RepoMetadata


def _finding() -> Finding:
    return Finding(
        id="x",
        category=FindingCategory.DEAD_CODE,
        severity=FindingSeverity.WARNING,
        title="t",
        description="d",
        qualified_name=None,
        file_path=None,
        start_line=None,
        end_line=None,
    )


def _kb() -> Mock:
    kb = Mock()
    kb.get_metadata.return_value = RepoMetadata(
        repo_name="repo", source="/x", ingested_at="t", files=(), symbol_count=0
    )
    kb.list_files.return_value = []
    kb.all_symbols.return_value = []
    kb.all_import_edges.return_value = []
    kb.all_call_edges.return_value = []
    kb.all_inherits_edges.return_value = []
    return kb


def test_aggregates_findings_from_all_analyzers():
    a1 = Mock()
    a1.name = "dead_code"
    a1.analyze.return_value = [_finding()]
    a2 = Mock()
    a2.name = "todo"
    a2.analyze.return_value = [_finding()]

    runner = AnalysisRunner(analyzers=[a1, a2])
    report = runner.run(_kb())

    assert len(report) == 2
    assert report.analyzers_run == ("dead_code", "todo")
    assert report.warnings == ()
    assert report.summary is None
    assert report.metadata.repo_name == "repo"
    assert isinstance(report.statistics, RepositoryStatistics)
    assert report.execution_time_seconds >= 0


def test_continues_after_a_failing_analyzer():
    failing = Mock()
    failing.name = "complexity"
    failing.analyze.side_effect = RuntimeError("boom")
    working = Mock()
    working.name = "todo"
    working.analyze.return_value = [_finding()]

    runner = AnalysisRunner(analyzers=[failing, working])
    report = runner.run(_kb())

    assert len(report) == 1
    assert report.analyzers_run == ("todo",)
    assert len(report.warnings) == 1
    assert report.warnings[0].analyzer == "complexity"
    assert "boom" in report.warnings[0].message


def test_default_analyzers_all_run_successfully():
    runner = AnalysisRunner()

    report = runner.run(_kb())

    assert report.analyzers_run == (
        "dead_code",
        "circular_dependency",
        "complexity",
        "todo",
        "architecture",
    )
    assert report.warnings == ()
