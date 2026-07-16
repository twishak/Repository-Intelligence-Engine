import logging

from codebase_agent.knowledge import KnowledgeBase
from codebase_agent.retrieval.evidence import EvidenceItem, EvidenceSource
from codebase_agent.retrieval.plan import RetrievalStep
from codebase_agent.retrieval.retrievers.resolution import (
    RESOLVED_CONFIDENCE,
    UNRESOLVED_CONFIDENCE,
    resolve_symbol_candidates,
    source_or,
)

logger = logging.getLogger(__name__)

_MAX_EDGES_PER_TARGET = 20


class CallGraphRetriever:
    """Who calls this symbol, and/or what it calls - the building block for
    impact analysis ("what would break if I changed X").
    """

    def retrieve(self, kb: KnowledgeBase, step: RetrievalStep) -> list[EvidenceItem]:
        if not step.target:
            logger.warning("call_graph step has no target - skipping")
            return []

        direction = (
            step.direction if step.direction in ("callers", "callees") else "both"
        )
        candidates = resolve_symbol_candidates(kb, step.target)
        if not candidates:
            return []

        items: list[EvidenceItem] = []
        for symbol, resolution_confidence in candidates:
            if direction in ("callers", "both"):
                for edge in kb.callers_of(symbol.qualified_name)[
                    :_MAX_EDGES_PER_TARGET
                ]:
                    items.append(_caller_item(kb, edge, resolution_confidence))
            if direction in ("callees", "both"):
                for edge in kb.callees_of(symbol.qualified_name)[
                    :_MAX_EDGES_PER_TARGET
                ]:
                    items.append(_callee_item(kb, edge, resolution_confidence))
        return items


def _caller_item(kb: KnowledgeBase, edge, resolution_confidence: float) -> EvidenceItem:
    fallback = f"{edge.caller_qualified_name} calls this at line {edge.line}"
    content = source_or(kb, edge.caller_qualified_name, fallback)
    callee = edge.callee_qualified_name or edge.callee_name
    return EvidenceItem(
        source=EvidenceSource.CALL_GRAPH,
        qualified_name=edge.caller_qualified_name,
        file_path=edge.file_path,
        start_line=edge.line,
        end_line=edge.line,
        content=content,
        explanation=f"Calls {callee} (line {edge.line})",
        confidence=min(resolution_confidence, RESOLVED_CONFIDENCE),
    )


def _callee_item(kb: KnowledgeBase, edge, resolution_confidence: float) -> EvidenceItem:
    resolved = edge.callee_qualified_name is not None
    target_name = edge.callee_qualified_name or edge.callee_name
    fallback = f"{edge.caller_qualified_name} calls {target_name} at line {edge.line}"
    content = source_or(kb, edge.callee_qualified_name, fallback)

    explanation = f"Called by {edge.caller_qualified_name} (line {edge.line})"
    if not resolved:
        explanation += " - target not resolved to a known symbol"

    return EvidenceItem(
        source=EvidenceSource.CALL_GRAPH,
        qualified_name=edge.callee_qualified_name,
        file_path=edge.file_path,
        start_line=edge.line,
        end_line=edge.line,
        content=content,
        explanation=explanation,
        confidence=min(
            resolution_confidence,
            RESOLVED_CONFIDENCE if resolved else UNRESOLVED_CONFIDENCE,
        ),
    )
