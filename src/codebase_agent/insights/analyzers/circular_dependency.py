import networkx as nx

from codebase_agent.insights.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    make_finding_id,
)
from codebase_agent.knowledge import KnowledgeBase


class CircularDependencyAnalyzer:
    """Finds import cycles among repo-local files.

    The one analyzer that genuinely needs graph traversal - builds a
    DiGraph from resolved import edges and runs nx.simple_cycles(). External
    (unresolved) imports can't participate in a cycle within the repo, so
    they're excluded from the graph entirely.
    """

    name = "circular_dependency"

    def analyze(self, kb: KnowledgeBase) -> list[Finding]:
        graph = nx.DiGraph()
        for edge in kb.all_import_edges():
            if edge.resolved_file:
                graph.add_edge(edge.importer_file, edge.resolved_file)

        findings = []
        for cycle in nx.simple_cycles(graph):
            if len(cycle) < 2:
                continue
            path = " -> ".join([*cycle, cycle[0]])
            shown = " -> ".join(cycle[:3]) + ("..." if len(cycle) > 3 else "")
            findings.append(
                Finding(
                    id=make_finding_id(FindingCategory.CIRCULAR_DEPENDENCY, path),
                    category=FindingCategory.CIRCULAR_DEPENDENCY,
                    severity=FindingSeverity.WARNING,
                    title=f"Circular import: {shown}",
                    description=f"These files import each other in a cycle: {path}",
                    qualified_name=None,
                    file_path=cycle[0],
                    start_line=None,
                    end_line=None,
                    details={"cycle_length": len(cycle), "cycle": path},
                )
            )
        return findings
