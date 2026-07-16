from codebase_agent.intelligence.graph_builder import build_graph
from codebase_agent.intelligence.models import (
    CallEdge,
    ImportEdge,
    InheritsEdge,
    RepoStructure,
    Symbol,
)


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


def test_symbol_nodes_carry_metadata_and_are_linked_to_their_file():
    structure = RepoStructure(symbols=[_symbol("pkg.a.foo")])
    graph = build_graph(structure)

    assert graph.nodes["pkg.a.foo"]["node_type"] == "symbol"
    assert graph.nodes["pkg.a.foo"]["kind"] == "function"
    assert graph.nodes["pkg.a.foo"]["file_path"] == "pkg/a.py"
    assert graph.nodes["pkg/a.py"]["node_type"] == "file"


def test_resolved_call_edge_connects_two_symbol_nodes():
    structure = RepoStructure(
        symbols=[_symbol("pkg.a.foo"), _symbol("pkg.a.bar")],
        call_edges=[CallEdge("pkg.a.foo", "bar", "pkg.a.bar", "pkg/a.py", 5)],
    )
    graph = build_graph(structure)

    assert graph.has_edge("pkg.a.foo", "pkg.a.bar")
    edge_data = graph.get_edge_data("pkg.a.foo", "pkg.a.bar")
    assert any(d["edge_type"] == "calls" for d in edge_data.values())


def test_unresolved_call_edge_points_at_external_node():
    structure = RepoStructure(
        symbols=[_symbol("pkg.a.foo")],
        call_edges=[CallEdge("pkg.a.foo", "os.getcwd", None, "pkg/a.py", 5)],
    )
    graph = build_graph(structure)

    assert graph.has_edge("pkg.a.foo", "external:os.getcwd")
    assert graph.nodes["external:os.getcwd"]["node_type"] == "external"


def test_import_edge_between_files():
    structure = RepoStructure(
        import_edges=[ImportEdge("pkg/a.py", "pkg.b", "pkg/b.py")]
    )
    graph = build_graph(structure)

    assert graph.has_edge("pkg/a.py", "pkg/b.py")


def test_unresolved_import_edge_points_at_external_node():
    structure = RepoStructure(import_edges=[ImportEdge("pkg/a.py", "numpy", None)])
    graph = build_graph(structure)

    assert graph.has_edge("pkg/a.py", "external:numpy")


def test_inherits_edge_resolved_and_unresolved():
    structure = RepoStructure(
        symbols=[
            _symbol("pkg.a.Base", kind="class"),
            _symbol("pkg.a.Child", kind="class"),
        ],
        inherits_edges=[
            InheritsEdge("pkg.a.Child", "Base", "pkg.a.Base"),
            InheritsEdge("pkg.a.Child", "abc.ABC", None),
        ],
    )
    graph = build_graph(structure)

    assert graph.has_edge("pkg.a.Child", "pkg.a.Base")
    assert graph.has_edge("pkg.a.Child", "external:abc.ABC")
