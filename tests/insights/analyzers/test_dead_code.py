from unittest.mock import Mock

from codebase_agent.insights.analyzers.dead_code import DeadCodeAnalyzer
from codebase_agent.insights.models import FindingSeverity
from codebase_agent.intelligence.models import Symbol


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


def test_flags_symbol_with_no_callers():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.helper")]
    kb.callers_of.return_value = []

    findings = DeadCodeAnalyzer().analyze(kb)

    assert len(findings) == 1
    assert findings[0].qualified_name == "pkg.a.helper"
    assert findings[0].severity == FindingSeverity.WARNING


def test_symbol_with_callers_is_not_flagged():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.helper")]
    kb.callers_of.return_value = [Mock()]

    assert DeadCodeAnalyzer().analyze(kb) == []


def test_excludes_main_dunders_and_test_symbols():
    kb = Mock()
    kb.all_symbols.return_value = [
        _symbol("pkg.a.main"),
        _symbol("pkg.a.MyClass.__init__", kind="method"),
        _symbol("pkg.a.test_something"),
        _symbol("tests.test_foo.test_bar", file_path="tests/test_foo.py"),
    ]
    kb.callers_of.return_value = []

    assert DeadCodeAnalyzer().analyze(kb) == []


def test_finding_id_is_stable_across_runs():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.helper")]
    kb.callers_of.return_value = []

    first = DeadCodeAnalyzer().analyze(kb)
    second = DeadCodeAnalyzer().analyze(kb)

    assert first[0].id == second[0].id
