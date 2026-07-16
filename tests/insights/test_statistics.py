from unittest.mock import Mock

from codebase_agent.insights.statistics import compute_statistics
from codebase_agent.intelligence.models import (
    CallEdge,
    ImportEdge,
    InheritsEdge,
    Symbol,
)


def _symbol(qualified_name: str, kind: str = "function") -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind=kind,
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        signature="...",
        docstring=None,
    )


def test_compute_statistics_counts_everything():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py", "pkg/b.py"]
    kb.all_symbols.return_value = [
        _symbol("pkg.a.foo", "function"),
        _symbol("pkg.a.Worker", "class"),
        _symbol("pkg.a.Worker.run", "method"),
    ]
    kb.all_import_edges.return_value = [
        ImportEdge("pkg/a.py", "pkg.b", "pkg/b.py"),
        ImportEdge("pkg/a.py", "numpy", None),
    ]
    kb.all_call_edges.return_value = [
        CallEdge("pkg.a.foo", "bar", "pkg.a.bar", "pkg/a.py", 3),
        CallEdge("pkg.a.foo", "os.getcwd", None, "pkg/a.py", 4),
    ]
    kb.all_inherits_edges.return_value = [
        InheritsEdge("pkg.a.Child", "Base", "pkg.a.Base")
    ]

    stats = compute_statistics(kb)

    assert stats.total_files == 2
    assert stats.total_symbols == 3
    assert stats.function_count == 1
    assert stats.class_count == 1
    assert stats.method_count == 1
    assert stats.total_import_edges == 2
    assert stats.resolved_import_edges == 1
    assert stats.total_call_edges == 2
    assert stats.resolved_call_edges == 1
    assert stats.total_inherits_edges == 1
