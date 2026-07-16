from dataclasses import dataclass
from enum import Enum

from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)


class EvidenceSource(str, Enum):
    SYMBOL = "symbol"
    SEMANTIC = "semantic"
    CALL_GRAPH = "call_graph"
    IMPORT_GRAPH = "import_graph"
    HIERARCHY = "hierarchy"


@dataclass(frozen=True)
class EvidenceItem:
    """One piece of retrieved evidence, normalized to a common shape
    regardless of which retriever produced it.

    Deliberately doesn't carry the underlying Symbol/CallEdge/ImportEdge/
    InheritsEdge/RetrievedChunk object - this is the abstraction boundary for
    everything downstream (answer generation, developer insights, a future
    API response); those object shapes are retrieval-internal.
    """

    source: EvidenceSource
    qualified_name: str | None
    file_path: str | None
    start_line: int | None
    end_line: int | None
    content: str
    explanation: str
    # Heuristic, not a calibrated probability - see per-retriever docstrings
    # for how each source computes it. Not comparable across sources.
    confidence: float | None


@dataclass(frozen=True)
class ExecutionWarning:
    step: RetrievalStep
    message: str


@dataclass(frozen=True)
class EvidenceBundle:
    question: str
    plan: RetrievalPlan
    items: tuple[EvidenceItem, ...]
    retrievers_used: tuple[RetrievalStrategy, ...]
    warnings: tuple[ExecutionWarning, ...]
    execution_time_seconds: float

    def by_source(self, source: EvidenceSource) -> list[EvidenceItem]:
        return [item for item in self.items if item.source == source]

    def sorted_by_confidence(self) -> list[EvidenceItem]:
        return sorted(
            self.items,
            key=lambda item: item.confidence if item.confidence is not None else 0.0,
            reverse=True,
        )

    def is_empty(self) -> bool:
        return len(self.items) == 0

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)
