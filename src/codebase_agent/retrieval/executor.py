import logging
import time
from typing import Protocol

from codebase_agent.knowledge import KnowledgeBase
from codebase_agent.retrieval.evidence import (
    EvidenceBundle,
    EvidenceItem,
    ExecutionWarning,
)
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)
from codebase_agent.retrieval.retrievers import (
    CallGraphRetriever,
    HierarchyRetriever,
    ImportRetriever,
    SemanticRetriever,
    SymbolRetriever,
)

logger = logging.getLogger(__name__)


class SpecializedRetriever(Protocol):
    def retrieve(
        self, kb: KnowledgeBase, step: RetrievalStep
    ) -> list[EvidenceItem]: ...


def _default_retrievers() -> dict[RetrievalStrategy, SpecializedRetriever]:
    return {
        RetrievalStrategy.SYMBOL_LOOKUP: SymbolRetriever(),
        RetrievalStrategy.SEMANTIC_SEARCH: SemanticRetriever(),
        RetrievalStrategy.CALL_GRAPH: CallGraphRetriever(),
        RetrievalStrategy.IMPORT_GRAPH: ImportRetriever(),
        RetrievalStrategy.HIERARCHY: HierarchyRetriever(),
    }


class RetrievalExecutor:
    """Executes a RetrievalPlan by dispatching each step to the matching
    specialized retriever and aggregating the results into an EvidenceBundle.

    A failing or unregistered step is recorded as a warning and skipped
    rather than aborting the whole plan - a multi-step plan (e.g. several
    retrievers for a compound question) is more useful partially-succeeding
    than fully failing on one bad step.
    """

    def __init__(
        self, retrievers: dict[RetrievalStrategy, SpecializedRetriever] | None = None
    ) -> None:
        self._retrievers = retrievers or _default_retrievers()

    def execute(
        self, kb: KnowledgeBase, question: str, plan: RetrievalPlan
    ) -> EvidenceBundle:
        start = time.perf_counter()
        items: list[EvidenceItem] = []
        warnings: list[ExecutionWarning] = []
        used: list[RetrievalStrategy] = []

        for step in plan.steps:
            if step.strategy not in used:
                used.append(step.strategy)

            retriever = self._retrievers.get(step.strategy)
            if retriever is None:
                message = f"No retriever registered for {step.strategy}"
                logger.warning(message)
                warnings.append(ExecutionWarning(step=step, message=message))
                continue

            try:
                items.extend(retriever.retrieve(kb, step))
            except Exception as e:
                logger.exception("Retrieval step failed: %s", step)
                warnings.append(ExecutionWarning(step=step, message=str(e)))

        items = _apply_max_results(items, plan.max_results)

        return EvidenceBundle(
            question=question,
            plan=plan,
            items=tuple(items),
            retrievers_used=tuple(used),
            warnings=tuple(warnings),
            execution_time_seconds=time.perf_counter() - start,
        )


def _apply_max_results(
    items: list[EvidenceItem], max_results: int | None
) -> list[EvidenceItem]:
    if max_results is None or max_results <= 0 or len(items) <= max_results:
        return items
    ranked = sorted(
        items,
        key=lambda item: item.confidence if item.confidence is not None else 0.0,
        reverse=True,
    )
    return ranked[:max_results]
