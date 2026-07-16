from pathlib import Path

from codebase_agent.ingestion.models import SourceFile
from codebase_agent.intelligence.python_extractor import extract_repo_structure
from codebase_agent.knowledge.snippets import SymbolSourceStore, build_symbol_sources


def _source(path: str, content: str) -> SourceFile:
    return SourceFile(
        path=path,
        absolute_path=f"/repo/{path}",
        language="python",
        content=content,
        line_count=len(content.splitlines()),
    )


def test_build_symbol_sources_slices_exact_symbol_text():
    source = _source(
        "pkg/a.py", "def foo():\n    return 1\n\n\ndef bar():\n    return 2\n"
    )
    structure = extract_repo_structure([source])

    sources = build_symbol_sources(structure, [source])

    assert sources["pkg.a.foo"] == "def foo():\n    return 1"
    assert sources["pkg.a.bar"] == "def bar():\n    return 2"


def test_store_round_trips(tmp_path: Path):
    store = SymbolSourceStore(base_dir=tmp_path)
    data = {"pkg.a.foo": "def foo():\n    return 1"}

    store.save("myrepo", data)
    loaded = store.load("myrepo")

    assert loaded == data


def test_load_missing_repo_returns_empty_dict(tmp_path: Path):
    store = SymbolSourceStore(base_dir=tmp_path)

    assert store.load("missing") == {}
