from unittest.mock import Mock

from codebase_agent.intelligence.models import ImportEdge
from codebase_agent.retrieval.plan import RetrievalStep, RetrievalStrategy
from codebase_agent.retrieval.retrievers.import_graph import ImportRetriever


def test_resolves_direct_file_path_target():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py", "pkg/b.py"]
    kb.imports_of.return_value = [ImportEdge("pkg/a.py", "pkg.b", "pkg/b.py")]
    kb.importers_of.return_value = []
    step = RetrievalStep(strategy=RetrievalStrategy.IMPORT_GRAPH, target="pkg/a.py")

    items = ImportRetriever().retrieve(kb, step)

    assert len(items) == 1
    assert items[0].file_path == "pkg/b.py"
    assert items[0].confidence == 1.0


def test_resolves_dotted_module_name_via_resolve_module():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py"]
    kb.resolve_module.return_value = "pkg/a.py"
    kb.imports_of.return_value = []
    kb.importers_of.return_value = [ImportEdge("pkg/c.py", "pkg.a", "pkg/a.py")]
    step = RetrievalStep(strategy=RetrievalStrategy.IMPORT_GRAPH, target="pkg.a")

    items = ImportRetriever().retrieve(kb, step)

    kb.resolve_module.assert_called_once_with("pkg.a")
    assert items[0].file_path == "pkg/c.py"


def test_unresolved_module_returns_empty():
    kb = Mock()
    kb.list_files.return_value = []
    kb.resolve_module.return_value = None
    step = RetrievalStep(
        strategy=RetrievalStrategy.IMPORT_GRAPH, target="unknown.module"
    )

    assert ImportRetriever().retrieve(kb, step) == []


def test_direction_imports_only_and_unresolved_confidence():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py"]
    kb.imports_of.return_value = [ImportEdge("pkg/a.py", "numpy", None)]
    step = RetrievalStep(
        strategy=RetrievalStrategy.IMPORT_GRAPH, target="pkg/a.py", direction="imports"
    )

    items = ImportRetriever().retrieve(kb, step)

    assert len(items) == 1
    assert items[0].confidence == 0.3
    kb.importers_of.assert_not_called()


def test_no_target_returns_empty():
    step = RetrievalStep(strategy=RetrievalStrategy.IMPORT_GRAPH)

    assert ImportRetriever().retrieve(Mock(), step) == []
