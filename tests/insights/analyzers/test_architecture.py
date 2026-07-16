from unittest.mock import Mock

from codebase_agent.insights.analyzers.architecture import ArchitectureAnalyzer
from codebase_agent.insights.models import FindingCategory
from codebase_agent.intelligence.models import ImportEdge, Symbol


def _symbol(
    qualified_name: str, file_path: str = "pkg/a.py", kind: str = "function"
) -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind=kind,
        file_path=file_path,
        start_line=1,
        end_line=2,
        signature="...",
        docstring=None,
    )


def test_package_structure_counts_files_per_package():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py", "pkg/b.py", "scripts/run.py"]
    kb.all_import_edges.return_value = []
    kb.all_symbols.return_value = []

    findings = ArchitectureAnalyzer().analyze(kb)
    package_counts = {
        f.details["package"]: f.details["file_count"]
        for f in findings
        if "package" in f.details
    }

    assert package_counts == {"pkg": 2, "scripts": 1}


def test_hub_files_need_at_least_two_importers():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py", "pkg/b.py", "pkg/hub.py"]
    kb.all_import_edges.return_value = [
        ImportEdge("pkg/a.py", "pkg.hub", "pkg/hub.py"),
        ImportEdge("pkg/b.py", "pkg.hub", "pkg/hub.py"),
    ]
    kb.all_symbols.return_value = []

    findings = ArchitectureAnalyzer().analyze(kb)
    hub_findings = [f for f in findings if "importer_count" in f.details]

    assert len(hub_findings) == 1
    assert hub_findings[0].file_path == "pkg/hub.py"
    assert hub_findings[0].details["importer_count"] == 2


def test_entry_point_detection():
    kb = Mock()
    kb.list_files.return_value = []
    kb.all_import_edges.return_value = []
    kb.all_symbols.return_value = [_symbol("scripts.run.main"), _symbol("pkg.a.helper")]

    findings = ArchitectureAnalyzer().analyze(kb)
    entry_points = [
        f
        for f in findings
        if f.category == FindingCategory.ARCHITECTURE and "Entry point" in f.title
    ]

    assert len(entry_points) == 1
    assert entry_points[0].qualified_name == "scripts.run.main"
