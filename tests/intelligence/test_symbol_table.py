from codebase_agent.intelligence.models import Symbol
from codebase_agent.intelligence.symbol_table import SymbolTable


def _symbol(
    qualified_name: str, file_path: str = "pkg/a.py", kind: str = "function"
) -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind=kind,
        file_path=file_path,
        start_line=1,
        end_line=2,
        signature=f"def {qualified_name}(): ...",
        docstring=None,
    )


def test_get_by_qualified_name():
    table = SymbolTable([_symbol("pkg.a.foo")])

    assert table.get("pkg.a.foo").qualified_name == "pkg.a.foo"
    assert table.get("missing") is None


def test_symbols_in_file():
    a = _symbol("pkg.a.foo", file_path="pkg/a.py")
    b = _symbol("pkg.b.bar", file_path="pkg/b.py")
    table = SymbolTable([a, b])

    assert [s.qualified_name for s in table.symbols_in_file("pkg/a.py")] == [
        "pkg.a.foo"
    ]
    assert table.symbols_in_file("missing.py") == []


def test_find_by_short_name_returns_all_matches():
    a = _symbol("pkg.a.Worker.run", file_path="pkg/a.py", kind="method")
    b = _symbol("pkg.b.Runner.run", file_path="pkg/b.py", kind="method")
    table = SymbolTable([a, b])

    matches = {s.qualified_name for s in table.find_by_short_name("run")}

    assert matches == {"pkg.a.Worker.run", "pkg.b.Runner.run"}


def test_len_and_iter():
    table = SymbolTable([_symbol("pkg.a.foo"), _symbol("pkg.a.bar")])

    assert len(table) == 2
    assert {s.qualified_name for s in table} == {"pkg.a.foo", "pkg.a.bar"}
