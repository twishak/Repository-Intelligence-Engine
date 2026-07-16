from dataclasses import dataclass
from enum import Enum


class RetrievalStrategy(str, Enum):
    SYMBOL_LOOKUP = "symbol_lookup"
    SEMANTIC_SEARCH = "semantic_search"
    CALL_GRAPH = "call_graph"
    IMPORT_GRAPH = "import_graph"
    HIERARCHY = "hierarchy"


class RetrievalPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True)
class RetrievalStep:
    strategy: RetrievalStrategy
    # Meaning depends on strategy: qualified/short symbol name (SYMBOL_LOOKUP,
    # CALL_GRAPH, HIERARCHY), file path or dotted module name (IMPORT_GRAPH).
    # Unused by SEMANTIC_SEARCH.
    target: str | None = None
    # Free-text search query. Only meaningful for SEMANTIC_SEARCH.
    query: str | None = None
    # "callers"|"callees"|"both" (CALL_GRAPH), "bases"|"subclasses"|"both"
    # (HIERARCHY), "imports"|"importers"|"both" (IMPORT_GRAPH). Unrecognized
    # or missing values fall back to "both" in the retriever, not here.
    direction: str | None = None


@dataclass(frozen=True)
class RetrievalPlan:
    steps: tuple[RetrievalStep, ...]
    # Planner's own label for the question, e.g. "impact_analysis" - logging
    # and debugging only, not consumed by the executor.
    intent: str | None = None
    # Reserved for future planners/executors; this planner always emits
    # NORMAL and the executor doesn't yet act on it.
    priority: RetrievalPriority = RetrievalPriority.NORMAL
    # Overall cap on evidence items across all steps combined, applied by the
    # executor after aggregating (highest-confidence items kept). None means
    # no cap.
    max_results: int | None = None
