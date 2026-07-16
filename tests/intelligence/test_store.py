from pathlib import Path

from codebase_agent.intelligence.models import (
    CallEdge,
    ImportEdge,
    InheritsEdge,
    RepoStructure,
    Symbol,
)
from codebase_agent.intelligence.store import RepoIntelligenceStore


def _structure() -> RepoStructure:
    return RepoStructure(
        symbols=[
            Symbol(
                qualified_name="pkg.a.foo",
                kind="function",
                file_path="pkg/a.py",
                start_line=1,
                end_line=3,
                signature="def foo(): ...",
                docstring="does foo",
                decorators=("staticmethod",),
            )
        ],
        import_edges=[ImportEdge("pkg/a.py", "pkg.b", "pkg/b.py")],
        call_edges=[CallEdge("pkg.a.foo", "bar", None, "pkg/a.py", 2)],
        inherits_edges=[InheritsEdge("pkg.a.Foo", "Base", None)],
    )


def test_save_then_load_round_trips(tmp_path: Path):
    store = RepoIntelligenceStore(base_dir=tmp_path)
    structure = _structure()

    store.save("myrepo", structure)
    loaded = store.load("myrepo")

    assert loaded == structure


def test_has_repo_false_before_save(tmp_path: Path):
    store = RepoIntelligenceStore(base_dir=tmp_path)

    assert store.has_repo("myrepo") is False


def test_has_repo_true_after_save(tmp_path: Path):
    store = RepoIntelligenceStore(base_dir=tmp_path)
    store.save("myrepo", _structure())

    assert store.has_repo("myrepo") is True


def test_load_missing_repo_returns_none(tmp_path: Path):
    store = RepoIntelligenceStore(base_dir=tmp_path)

    assert store.load("missing") is None
