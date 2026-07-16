from unittest.mock import Mock

from codebase_agent.intelligence.models import InheritsEdge, Symbol
from codebase_agent.retrieval.plan import RetrievalStep, RetrievalStrategy
from codebase_agent.retrieval.retrievers.hierarchy import HierarchyRetriever


def _symbol(qualified_name: str) -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind="class",
        file_path="pkg/a.py",
        start_line=1,
        end_line=5,
        signature="...",
        docstring=None,
    )


def test_base_classes_resolved():
    kb = Mock()
    kb.get_symbol.side_effect = lambda name: (
        _symbol(name) if name in ("pkg.a.Child", "pkg.a.Base") else None
    )
    kb.find_symbols_by_name.return_value = []
    kb.base_classes_of.return_value = [
        InheritsEdge("pkg.a.Child", "Base", "pkg.a.Base")
    ]
    kb.get_source.return_value = None
    step = RetrievalStep(
        strategy=RetrievalStrategy.HIERARCHY, target="pkg.a.Child", direction="bases"
    )

    items = HierarchyRetriever().retrieve(kb, step)

    assert len(items) == 1
    assert items[0].qualified_name == "pkg.a.Base"
    assert items[0].confidence == 1.0
    assert items[0].file_path == "pkg/a.py"


def test_unresolved_base_class():
    kb = Mock()
    kb.get_symbol.side_effect = lambda name: (
        _symbol(name) if name == "pkg.a.Thing" else None
    )
    kb.base_classes_of.return_value = [InheritsEdge("pkg.a.Thing", "abc.ABC", None)]
    kb.get_source.return_value = None
    step = RetrievalStep(
        strategy=RetrievalStrategy.HIERARCHY, target="pkg.a.Thing", direction="bases"
    )

    items = HierarchyRetriever().retrieve(kb, step)

    assert items[0].qualified_name is None
    assert items[0].confidence == 0.3
    assert "external" in items[0].explanation


def test_subclasses():
    kb = Mock()
    kb.get_symbol.side_effect = lambda name: _symbol(name)
    kb.subclasses_of.return_value = [InheritsEdge("pkg.a.Child", "Base", "pkg.a.Base")]
    kb.get_source.return_value = None
    step = RetrievalStep(
        strategy=RetrievalStrategy.HIERARCHY,
        target="pkg.a.Base",
        direction="subclasses",
    )

    items = HierarchyRetriever().retrieve(kb, step)

    assert items[0].qualified_name == "pkg.a.Child"
    assert items[0].explanation == "Subclass of pkg.a.Base"


def test_no_target_returns_empty():
    step = RetrievalStep(strategy=RetrievalStrategy.HIERARCHY)

    assert HierarchyRetriever().retrieve(Mock(), step) == []
