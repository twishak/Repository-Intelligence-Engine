from codebase_agent.insights.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    RepositoryReport,
    RepositoryStatistics,
    make_finding_id,
)
from codebase_agent.knowledge import RepoMetadata


def _finding(
    category: FindingCategory = FindingCategory.DEAD_CODE,
    severity: FindingSeverity = FindingSeverity.WARNING,
) -> Finding:
    return Finding(
        id=make_finding_id(category, "pkg.a.foo"),
        category=category,
        severity=severity,
        title="t",
        description="d",
        qualified_name="pkg.a.foo",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
    )


def _stats() -> RepositoryStatistics:
    return RepositoryStatistics(
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
    )


def _metadata() -> RepoMetadata:
    return RepoMetadata(
        repo_name="repo",
        source="/x",
        ingested_at="t",
        files=("pkg/a.py",),
        symbol_count=1,
    )


def _report(findings: list[Finding]) -> RepositoryReport:
    return RepositoryReport(
        metadata=_metadata(),
        statistics=_stats(),
        findings=tuple(findings),
        summary=None,
        generated_at="t",
        analyzers_run=(),
        warnings=(),
        execution_time_seconds=0.0,
    )


def test_make_finding_id_is_deterministic_and_category_sensitive():
    a = make_finding_id(FindingCategory.DEAD_CODE, "pkg.a.foo", "3")
    b = make_finding_id(FindingCategory.DEAD_CODE, "pkg.a.foo", "3")
    c = make_finding_id(FindingCategory.COMPLEXITY, "pkg.a.foo", "3")

    assert a == b
    assert a != c


def test_by_category():
    a = _finding(category=FindingCategory.DEAD_CODE)
    b = _finding(category=FindingCategory.TODO)
    report = _report([a, b])

    assert report.by_category(FindingCategory.DEAD_CODE) == [a]


def test_by_severity():
    a = _finding(severity=FindingSeverity.WARNING)
    b = _finding(severity=FindingSeverity.INFO)
    report = _report([a, b])

    assert report.by_severity(FindingSeverity.INFO) == [b]


def test_finding_counts():
    report = _report(
        [
            _finding(category=FindingCategory.DEAD_CODE),
            _finding(category=FindingCategory.DEAD_CODE),
            _finding(category=FindingCategory.TODO),
        ]
    )

    assert report.finding_counts() == {
        FindingCategory.DEAD_CODE: 2,
        FindingCategory.TODO: 1,
    }


def test_is_empty_len_and_iter():
    empty = _report([])
    assert empty.is_empty() is True
    assert len(empty) == 0

    findings = [_finding(), _finding()]
    report = _report(findings)
    assert report.is_empty() is False
    assert len(report) == 2
    assert list(report) == findings
