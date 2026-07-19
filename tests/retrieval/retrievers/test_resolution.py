from unittest.mock import Mock

from codebase_agent.intelligence.models import Symbol
from codebase_agent.retrieval.retrievers.resolution import resolve_symbol_candidates


def _symbol(qualified_name: str) -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind="method",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        signature="...",
        docstring=None,
    )


def test_exact_qualified_name_match_short_circuits():
    kb = Mock()
    kb.get_symbol.return_value = _symbol("pkg.a.Worker.run")

    candidates = resolve_symbol_candidates(kb, "pkg.a.Worker.run")

    assert candidates == [(kb.get_symbol.return_value, 1.0)]
    kb.find_symbols_by_name.assert_not_called()
    kb.all_symbols.assert_not_called()


def test_falls_back_to_partial_dotted_suffix_match():
    # Regression test: a real question ("what calls Session.request")
    # produced this exact target. It's neither the full qualified name
    # (requests.sessions.Session.request) nor the bare short name
    # (request), so both the exact and short-name lookups miss - only a
    # suffix match against the full qualified name finds it.
    kb = Mock()
    kb.get_symbol.return_value = None
    kb.find_symbols_by_name.return_value = []
    kb.all_symbols.return_value = [
        _symbol("requests.api.request"),
        _symbol("requests.sessions.Session.request"),
    ]

    candidates = resolve_symbol_candidates(kb, "Session.request")

    assert candidates == [
        (_symbol("requests.sessions.Session.request"), 1.0),
    ]


def test_suffix_match_is_ambiguous_across_multiple_classes():
    kb = Mock()
    kb.get_symbol.return_value = None
    kb.find_symbols_by_name.return_value = []
    kb.all_symbols.return_value = [
        _symbol("pkg.a.Worker.run"),
        _symbol("pkg.b.Worker.run"),
    ]

    candidates = resolve_symbol_candidates(kb, "Worker.run")

    assert len(candidates) == 2
    assert all(confidence == 0.6 for _symbol, confidence in candidates)


def test_no_dot_in_target_does_not_trigger_suffix_scan():
    kb = Mock()
    kb.get_symbol.return_value = None
    kb.find_symbols_by_name.return_value = []

    candidates = resolve_symbol_candidates(kb, "missing")

    assert candidates == []
    kb.all_symbols.assert_not_called()


def test_unresolved_suffix_returns_empty():
    kb = Mock()
    kb.get_symbol.return_value = None
    kb.find_symbols_by_name.return_value = []
    kb.all_symbols.return_value = [_symbol("pkg.a.Worker.run")]

    candidates = resolve_symbol_candidates(kb, "Other.run")

    assert candidates == []
