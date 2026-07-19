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

    If every step in the plan is a structured strategy (symbol_lookup,
    call_graph, import_graph, hierarchy - anything but semantic_search) and
    none of them produced evidence, falls back to a single semantic_search
    over the raw question. This is a safety net for planner target-extraction
    mistakes (a hallucinated or malformed identifier resolves to nothing even
    though the planner picked the right strategy) - it never runs if the plan
    already included semantic_search, and it only ever runs once.
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

        if not items and _is_purely_structured(plan.steps):
            logger.warning(
                "Structured retrieval (%s) returned no evidence for %r - "
                "falling back to semantic_search over the raw question. This "
                "usually means the planner's target didn't resolve to a real "
                "symbol/file (e.g. a hallucinated or malformed name).",
                ", ".join(step.strategy.value for step in plan.steps),
                question,
            )
            fallback_step = RetrievalStep(
                strategy=RetrievalStrategy.SEMANTIC_SEARCH, query=question
            )
            retriever = self._retrievers.get(RetrievalStrategy.SEMANTIC_SEARCH)
            if retriever is None:
                message = "No retriever registered for semantic_search fallback"
                logger.warning(message)
                warnings.append(ExecutionWarning(step=fallback_step, message=message))
            else:
                if RetrievalStrategy.SEMANTIC_SEARCH not in used:
                    used.append(RetrievalStrategy.SEMANTIC_SEARCH)
                try:
                    items.extend(retriever.retrieve(kb, fallback_step))
                except Exception as e:
                    logger.exception("Semantic-search fallback failed")
                    warnings.append(
                        ExecutionWarning(step=fallback_step, message=str(e))
                    )

        items = _apply_max_results(items, plan.max_results)

        return EvidenceBundle(
            question=question,
            plan=plan,
            items=tuple(items),
            retrievers_used=tuple(used),
            warnings=tuple(warnings),
            execution_time_seconds=time.perf_counter() - start,
        )


def _is_purely_structured(steps: tuple[RetrievalStep, ...]) -> bool:
    """True if every step is a non-semantic strategy - i.e. the plan hasn't
    already tried semantic_search, so falling back to it is still worthwhile.
    """
    return all(step.strategy != RetrievalStrategy.SEMANTIC_SEARCH for step in steps)


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
