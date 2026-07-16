from unittest.mock import Mock

from codebase_agent.intelligence.models import (
    CallEdge,
    ImportEdge,
    InheritsEdge,
    RepoStructure,
    Symbol,
)
from codebase_agent.intelligence.symbol_table import SymbolTable
from codebase_agent.knowledge.default import DefaultKnowledgeBase
from codebase_agent.knowledge.metadata import RepoMetadata
from codebase_agent.storage.models import RetrievedChunk


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


def _kb(**overrides) -> DefaultKnowledgeBase:
    structure = overrides.pop("structure", RepoStructure())
    metadata = overrides.pop(
        "metadata",
        RepoMetadata(
            repo_name="myrepo",
            source="/x",
            ingested_at="t",
            files=("pkg/a.py", "pkg/b.py"),
            symbol_count=len(structure.symbols),
        ),
    )
    defaults = dict(
        repo_name="myrepo",
        symbol_table=SymbolTable(structure.symbols),
        structure=structure,
        sources={},
        file_sources={},
        vector_store=Mock(),
        embedder=Mock(),
        metadata=metadata,
        metadata_store=Mock(),
    )
    defaults.update(overrides)
    return DefaultKnowledgeBase(**defaults)


def test_get_symbol():
    structure = RepoStructure(symbols=[_symbol("pkg.a.foo")])
    kb = _kb(structure=structure)

    assert kb.get_symbol("pkg.a.foo").qualified_name == "pkg.a.foo"
    assert kb.get_symbol("missing") is None


def test_find_symbols_by_name():
    structure = RepoStructure(
        symbols=[
            _symbol("pkg.a.Worker.run", kind="method"),
            _symbol("pkg.b.Runner.run", file_path="pkg/b.py", kind="method"),
        ]
    )
    kb = _kb(structure=structure)

    names = {s.qualified_name for s in kb.find_symbols_by_name("run")}

    assert names == {"pkg.a.Worker.run", "pkg.b.Runner.run"}


def test_symbols_in_file():
    structure = RepoStructure(
        symbols=[_symbol("pkg.a.foo"), _symbol("pkg.b.bar", file_path="pkg/b.py")]
    )
    kb = _kb(structure=structure)

    assert [s.qualified_name for s in kb.symbols_in_file("pkg/a.py")] == ["pkg.a.foo"]


def test_list_files_from_metadata():
    kb = _kb()

    assert kb.list_files() == ["pkg/a.py", "pkg/b.py"]


def test_resolve_module():
    kb = _kb()

    assert kb.resolve_module("pkg.a") == "pkg/a.py"
    assert kb.resolve_module("missing.module") is None


def test_resolve_module_omits_the_src_prefix_in_a_src_layout_repo():
    metadata = RepoMetadata(
        repo_name="myrepo",
        source="/x",
        ingested_at="t",
        files=("src/pkg/a.py",),
        symbol_count=0,
    )
    kb = _kb(metadata=metadata)

    assert kb.resolve_module("pkg.a") == "src/pkg/a.py"


def test_callers_and_callees_of():
    structure = RepoStructure(
        call_edges=[
            CallEdge("pkg.a.foo", "bar", "pkg.a.bar", "pkg/a.py", 3),
            CallEdge("pkg.a.foo", "os.getcwd", None, "pkg/a.py", 4),
        ]
    )
    kb = _kb(structure=structure)

    assert len(kb.callees_of("pkg.a.foo")) == 2

    callers = kb.callers_of("pkg.a.bar")
    assert len(callers) == 1
    assert callers[0].caller_qualified_name == "pkg.a.foo"


def test_imports_and_importers_of():
    structure = RepoStructure(
        import_edges=[ImportEdge("pkg/a.py", "pkg.b", "pkg/b.py")]
    )
    kb = _kb(structure=structure)

    assert [e.imported_module for e in kb.imports_of("pkg/a.py")] == ["pkg.b"]
    assert [e.importer_file for e in kb.importers_of("pkg/b.py")] == ["pkg/a.py"]


def test_base_classes_and_subclasses_of():
    structure = RepoStructure(
        inherits_edges=[InheritsEdge("pkg.a.Child", "Base", "pkg.a.Base")]
    )
    kb = _kb(structure=structure)

    assert [e.base_qualified_name for e in kb.base_classes_of("pkg.a.Child")] == [
        "pkg.a.Base"
    ]
    assert [e.class_qualified_name for e in kb.subclasses_of("pkg.a.Base")] == [
        "pkg.a.Child"
    ]


def test_get_source():
    kb = _kb(sources={"pkg.a.foo": "def foo(): ..."})

    assert kb.get_source("pkg.a.foo") == "def foo(): ..."
    assert kb.get_source("missing") is None


def test_get_file_source():
    kb = _kb(file_sources={"pkg/a.py": "def foo(): ...\n"})

    assert kb.get_file_source("pkg/a.py") == "def foo(): ...\n"
    assert kb.get_file_source("missing.py") is None


def test_all_symbols():
    structure = RepoStructure(
        symbols=[_symbol("pkg.a.foo"), _symbol("pkg.b.bar", file_path="pkg/b.py")]
    )
    kb = _kb(structure=structure)

    assert {s.qualified_name for s in kb.all_symbols()} == {"pkg.a.foo", "pkg.b.bar"}


def test_all_import_edges():
    structure = RepoStructure(
        import_edges=[ImportEdge("pkg/a.py", "pkg.b", "pkg/b.py")]
    )
    kb = _kb(structure=structure)

    assert kb.all_import_edges() == structure.import_edges


def test_all_call_edges():
    structure = RepoStructure(
        call_edges=[CallEdge("pkg.a.foo", "bar", "pkg.a.bar", "pkg/a.py", 3)]
    )
    kb = _kb(structure=structure)

    assert kb.all_call_edges() == structure.call_edges


def test_all_inherits_edges():
    structure = RepoStructure(
        inherits_edges=[InheritsEdge("pkg.a.Child", "Base", "pkg.a.Base")]
    )
    kb = _kb(structure=structure)

    assert kb.all_inherits_edges() == structure.inherits_edges


def test_semantic_search_delegates_to_embedder_and_vector_store():
    embedder = Mock()
    embedder.embed.return_value = [[0.1, 0.2]]
    vector_store = Mock()
    chunk = RetrievedChunk(
        id="x",
        file_path="pkg/a.py",
        chunk_type="function",
        qualified_name="pkg.a.foo",
        start_line=1,
        end_line=2,
        content="def foo(): ...",
        docstring=None,
        distance=0.1,
    )
    vector_store.query.return_value = [chunk]
    kb = _kb(embedder=embedder, vector_store=vector_store)

    results = kb.semantic_search("find foo", k=3)

    embedder.embed.assert_called_once_with(["find foo"])
    vector_store.query.assert_called_once_with("myrepo", [0.1, 0.2], n_results=3)
    assert results == [chunk]


def test_get_metadata_returns_stored_metadata():
    metadata = RepoMetadata(
        repo_name="myrepo", source="/x", ingested_at="t", files=(), symbol_count=0
    )
    kb = _kb(metadata=metadata)

    assert kb.get_metadata() == metadata


def test_set_summary_persists_and_updates_in_memory_copy():
    metadata_store = Mock()
    kb = _kb(metadata_store=metadata_store)

    kb.set_summary("A summary.")

    assert kb.get_metadata().summary == "A summary."
    metadata_store.save.assert_called_once()
    saved = metadata_store.save.call_args.args[0]
    assert saved.summary == "A summary."
