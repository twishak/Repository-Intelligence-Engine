from unittest.mock import Mock

from codebase_agent.intelligence.models import Symbol
from codebase_agent.retrieval.plan import RetrievalStep, RetrievalStrategy
from codebase_agent.retrieval.retrievers.symbol import SymbolRetriever


def _symbol(qualified_name: str = "pkg.a.foo") -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind="function",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        signature="def foo(): ...",
        docstring=None,
    )


def test_exact_match_returns_high_confidence_item():
    kb = Mock()
    kb.get_symbol.return_value = _symbol()
    kb.get_source.return_value = "def foo(): ..."
    step = RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="pkg.a.foo")

    items = SymbolRetriever().retrieve(kb, step)

    assert len(items) == 1
    assert items[0].qualified_name == "pkg.a.foo"
    assert items[0].confidence == 1.0
    assert items[0].content == "def foo(): ..."


def test_falls_back_to_short_name_matches():
    kb = Mock()
    kb.get_symbol.return_value = None
    kb.find_symbols_by_name.return_value = [
        _symbol("pkg.a.Worker.run"),
        _symbol("pkg.b.Runner.run"),
    ]
    kb.get_source.return_value = None
    step = RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="run")

    items = SymbolRetriever().retrieve(kb, step)

    assert {i.qualified_name for i in items} == {"pkg.a.Worker.run", "pkg.b.Runner.run"}
    assert all(i.confidence == 0.6 for i in items)


def test_falls_back_to_signature_when_no_source():
    kb = Mock()
    kb.get_symbol.return_value = _symbol()
    kb.get_source.return_value = None
    step = RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="pkg.a.foo")

    items = SymbolRetriever().retrieve(kb, step)

    assert items[0].content == "def foo(): ..."


def test_no_target_returns_empty():
    step = RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP)

    assert SymbolRetriever().retrieve(Mock(), step) == []


def test_no_matches_returns_empty():
    kb = Mock()
    kb.get_symbol.return_value = None
    kb.find_symbols_by_name.return_value = []
    step = RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="missing")

    assert SymbolRetriever().retrieve(kb, step) == []
