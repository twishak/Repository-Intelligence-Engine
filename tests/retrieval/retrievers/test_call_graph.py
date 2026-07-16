from unittest.mock import Mock

from codebase_agent.intelligence.models import CallEdge, Symbol
from codebase_agent.retrieval.plan import RetrievalStep, RetrievalStrategy
from codebase_agent.retrieval.retrievers.call_graph import CallGraphRetriever


def _symbol(qualified_name: str = "pkg.a.foo") -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind="function",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        signature="...",
        docstring=None,
    )


def test_returns_both_callers_and_callees_by_default():
    kb = Mock()
    kb.get_symbol.return_value = _symbol("pkg.a.foo")
    kb.callers_of.return_value = [
        CallEdge("pkg.b.bar", "foo", "pkg.a.foo", "pkg/b.py", 3)
    ]
    kb.callees_of.return_value = [
        CallEdge("pkg.a.foo", "baz", "pkg.a.baz", "pkg/a.py", 5)
    ]
    kb.get_source.return_value = None
    step = RetrievalStep(strategy=RetrievalStrategy.CALL_GRAPH, target="pkg.a.foo")

    items = CallGraphRetriever().retrieve(kb, step)

    assert len(items) == 2
    kb.callers_of.assert_called_once_with("pkg.a.foo")
    kb.callees_of.assert_called_once_with("pkg.a.foo")


def test_direction_callers_only():
    kb = Mock()
    kb.get_symbol.return_value = _symbol()
    kb.callers_of.return_value = [
        CallEdge("pkg.b.bar", "foo", "pkg.a.foo", "pkg/b.py", 3)
    ]
    kb.get_source.return_value = None
    step = RetrievalStep(
        strategy=RetrievalStrategy.CALL_GRAPH, target="pkg.a.foo", direction="callers"
    )

    items = CallGraphRetriever().retrieve(kb, step)

    assert len(items) == 1
    kb.callees_of.assert_not_called()


def test_unresolved_callee_gets_lower_confidence():
    kb = Mock()
    kb.get_symbol.return_value = _symbol()
    kb.callers_of.return_value = []
    kb.callees_of.return_value = [
        CallEdge("pkg.a.foo", "os.getcwd", None, "pkg/a.py", 5)
    ]
    kb.get_source.return_value = None
    step = RetrievalStep(
        strategy=RetrievalStrategy.CALL_GRAPH, target="pkg.a.foo", direction="callees"
    )

    items = CallGraphRetriever().retrieve(kb, step)

    assert items[0].confidence == 0.3
    assert "not resolved" in items[0].explanation


def test_falls_back_to_short_name_and_caps_confidence():
    kb = Mock()
    kb.get_symbol.return_value = None
    kb.find_symbols_by_name.return_value = [
        _symbol("pkg.a.Worker.run"),
        _symbol("pkg.b.Runner.run"),
    ]
    kb.callers_of.return_value = []
    kb.callees_of.return_value = [
        CallEdge("pkg.a.Worker.run", "helper", "pkg.a.helper", "pkg/a.py", 2)
    ]
    kb.get_source.return_value = None
    step = RetrievalStep(
        strategy=RetrievalStrategy.CALL_GRAPH, target="run", direction="callees"
    )

    items = CallGraphRetriever().retrieve(kb, step)

    assert all(i.confidence == 0.6 for i in items)


def test_no_target_returns_empty():
    step = RetrievalStep(strategy=RetrievalStrategy.CALL_GRAPH)

    assert CallGraphRetriever().retrieve(Mock(), step) == []


def test_unknown_target_returns_empty():
    kb = Mock()
    kb.get_symbol.return_value = None
    kb.find_symbols_by_name.return_value = []
    step = RetrievalStep(strategy=RetrievalStrategy.CALL_GRAPH, target="missing")

    assert CallGraphRetriever().retrieve(kb, step) == []
