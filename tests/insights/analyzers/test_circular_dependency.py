from unittest.mock import Mock

from codebase_agent.insights.analyzers.circular_dependency import (
    CircularDependencyAnalyzer,
)
from codebase_agent.intelligence.models import ImportEdge


def test_detects_a_simple_cycle():
    kb = Mock()
    kb.all_import_edges.return_value = [
        ImportEdge("pkg/a.py", "pkg.b", "pkg/b.py"),
        ImportEdge("pkg/b.py", "pkg.a", "pkg/a.py"),
    ]

    findings = CircularDependencyAnalyzer().analyze(kb)

    assert len(findings) == 1
    assert findings[0].details["cycle_length"] == 2


def test_no_cycle_produces_no_findings():
    kb = Mock()
    kb.all_import_edges.return_value = [ImportEdge("pkg/a.py", "pkg.b", "pkg/b.py")]

    assert CircularDependencyAnalyzer().analyze(kb) == []


def test_unresolved_imports_are_excluded_from_the_graph():
    kb = Mock()
    kb.all_import_edges.return_value = [ImportEdge("pkg/a.py", "numpy", None)]

    assert CircularDependencyAnalyzer().analyze(kb) == []
