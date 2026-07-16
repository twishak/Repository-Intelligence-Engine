from unittest.mock import Mock

from codebase_agent.insights.analyzers.complexity import ComplexityAnalyzer
from codebase_agent.intelligence.models import Symbol


def _symbol(qualified_name: str, kind: str = "function") -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind=kind,
        file_path="pkg/a.py",
        start_line=1,
        end_line=10,
        signature="...",
        docstring=None,
    )


def _branchy_source(branches: int) -> str:
    lines = ["def foo():"]
    for i in range(branches):
        lines.append(f"    if x == {i}:")
        lines.append("        pass")
    return "\n".join(lines)


def test_flags_high_complexity_function():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.foo")]
    kb.get_source.return_value = _branchy_source(12)

    findings = ComplexityAnalyzer(threshold=10).analyze(kb)

    assert len(findings) == 1
    assert findings[0].details["cyclomatic_complexity"] == 13


def test_simple_function_not_flagged():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.foo")]
    kb.get_source.return_value = "def foo():\n    return 1\n"

    assert ComplexityAnalyzer(threshold=10).analyze(kb) == []


def test_handles_indented_method_source_via_dedent():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.Worker.run", kind="method")]
    body = "".join(f"        if x == {i}:\n            pass\n" for i in range(12))
    kb.get_source.return_value = "    def run(self):\n" + body

    findings = ComplexityAnalyzer(threshold=10).analyze(kb)

    assert len(findings) == 1


def test_skips_class_symbols():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.Worker", kind="class")]
    kb.get_source.return_value = "class Worker:\n    pass\n"

    assert ComplexityAnalyzer().analyze(kb) == []


def test_skips_unparseable_source_without_crashing():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.foo")]
    kb.get_source.return_value = "def foo(:\n    pass\n"

    assert ComplexityAnalyzer().analyze(kb) == []


def test_missing_source_is_skipped():
    kb = Mock()
    kb.all_symbols.return_value = [_symbol("pkg.a.foo")]
    kb.get_source.return_value = None

    assert ComplexityAnalyzer().analyze(kb) == []
