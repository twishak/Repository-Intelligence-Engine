from collections import Counter

from codebase_agent.insights.models import RepositoryStatistics
from codebase_agent.knowledge import KnowledgeBase


def compute_statistics(kb: KnowledgeBase) -> RepositoryStatistics:
    """Generic repo facts, derived from KnowledgeBase's whole-repo
    primitives - independent of which (if any) analyzers are registered.
    """
    symbols = kb.all_symbols()
    import_edges = kb.all_import_edges()
    call_edges = kb.all_call_edges()
    inherits_edges = kb.all_inherits_edges()
    kind_counts = Counter(s.kind for s in symbols)

    return RepositoryStatistics(
        total_files=len(kb.list_files()),
        total_symbols=len(symbols),
        function_count=kind_counts.get("function", 0),
        method_count=kind_counts.get("method", 0),
        class_count=kind_counts.get("class", 0),
        total_import_edges=len(import_edges),
        total_call_edges=len(call_edges),
        total_inherits_edges=len(inherits_edges),
        resolved_call_edges=sum(
            1 for e in call_edges if e.callee_qualified_name is not None
        ),
        resolved_import_edges=sum(
            1 for e in import_edges if e.resolved_file is not None
        ),
    )
