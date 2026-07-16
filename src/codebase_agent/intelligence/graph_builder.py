import networkx as nx

from codebase_agent.intelligence.models import RepoStructure

EDGE_IMPORTS = "imports"
EDGE_CALLS = "calls"
EDGE_INHERITS = "inherits"

NODE_SYMBOL = "symbol"
NODE_FILE = "file"
NODE_EXTERNAL = "external"


def build_graph(structure: RepoStructure) -> nx.MultiDiGraph:
    """Build a NetworkX graph over a repo's extracted structure.

    Nodes are either symbols (functions/methods/classes, keyed by qualified
    name), files (keyed by repo-relative path), or "external" stubs for
    callees/bases/imports that couldn't be resolved to repo code - kept as
    nodes rather than dropped, so e.g. "what does this file import" still
    surfaces third-party dependencies.
    """
    graph = nx.MultiDiGraph()

    for symbol in structure.symbols:
        graph.add_node(
            symbol.qualified_name,
            node_type=NODE_SYMBOL,
            kind=symbol.kind,
            file_path=symbol.file_path,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
        )
        _ensure_file_node(graph, symbol.file_path)

    for edge in structure.import_edges:
        _ensure_file_node(graph, edge.importer_file)
        target = edge.resolved_file or _external_node(graph, edge.imported_module)
        if edge.resolved_file:
            _ensure_file_node(graph, edge.resolved_file)
        graph.add_edge(
            edge.importer_file,
            target,
            edge_type=EDGE_IMPORTS,
            module=edge.imported_module,
        )

    for edge in structure.call_edges:
        target = edge.callee_qualified_name or _external_node(graph, edge.callee_name)
        graph.add_edge(
            edge.caller_qualified_name,
            target,
            edge_type=EDGE_CALLS,
            file_path=edge.file_path,
            line=edge.line,
        )

    for edge in structure.inherits_edges:
        target = edge.base_qualified_name or _external_node(graph, edge.base_name)
        graph.add_edge(edge.class_qualified_name, target, edge_type=EDGE_INHERITS)

    return graph


def _ensure_file_node(graph: nx.MultiDiGraph, file_path: str) -> None:
    if file_path not in graph:
        graph.add_node(file_path, node_type=NODE_FILE)


def _external_node(graph: nx.MultiDiGraph, name: str) -> str:
    node_id = f"external:{name}"
    if node_id not in graph:
        graph.add_node(node_id, node_type=NODE_EXTERNAL, name=name)
    return node_id
