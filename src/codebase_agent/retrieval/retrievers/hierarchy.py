import logging

from codebase_agent.intelligence.models import InheritsEdge
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


class HierarchyRetriever:
    """A class's base classes, and/or its subclasses - inheritance questions."""

    def retrieve(self, kb: KnowledgeBase, step: RetrievalStep) -> list[EvidenceItem]:
        if not step.target:
            logger.warning("hierarchy step has no target - skipping")
            return []

        direction = (
            step.direction if step.direction in ("bases", "subclasses") else "both"
        )
        candidates = resolve_symbol_candidates(kb, step.target)
        if not candidates:
            return []

        items: list[EvidenceItem] = []
        for symbol, resolution_confidence in candidates:
            if direction in ("bases", "both"):
                for edge in kb.base_classes_of(symbol.qualified_name):
                    items.append(_base_item(kb, edge, resolution_confidence))
            if direction in ("subclasses", "both"):
                for edge in kb.subclasses_of(symbol.qualified_name):
                    items.append(_subclass_item(kb, edge, resolution_confidence))
        return items


def _base_item(
    kb: KnowledgeBase, edge: InheritsEdge, resolution_confidence: float
) -> EvidenceItem:
    resolved = edge.base_qualified_name is not None
    symbol = kb.get_symbol(edge.base_qualified_name) if resolved else None
    fallback = f"{edge.class_qualified_name} inherits from {edge.base_name}"
    content = source_or(kb, edge.base_qualified_name, fallback)

    explanation = f"Base class of {edge.class_qualified_name}"
    if not resolved:
        explanation += " (external, not part of this repo)"

    return EvidenceItem(
        source=EvidenceSource.HIERARCHY,
        qualified_name=edge.base_qualified_name,
        file_path=symbol.file_path if symbol else None,
        start_line=symbol.start_line if symbol else None,
        end_line=symbol.end_line if symbol else None,
        content=content,
        explanation=explanation,
        confidence=min(
            resolution_confidence,
            RESOLVED_CONFIDENCE if resolved else UNRESOLVED_CONFIDENCE,
        ),
    )


def _subclass_item(
    kb: KnowledgeBase, edge: InheritsEdge, resolution_confidence: float
) -> EvidenceItem:
    symbol = kb.get_symbol(edge.class_qualified_name)
    fallback = f"{edge.class_qualified_name} inherits from {edge.base_name}"
    content = source_or(kb, edge.class_qualified_name, fallback)

    return EvidenceItem(
        source=EvidenceSource.HIERARCHY,
        qualified_name=edge.class_qualified_name,
        file_path=symbol.file_path if symbol else None,
        start_line=symbol.start_line if symbol else None,
        end_line=symbol.end_line if symbol else None,
        content=content,
        explanation=f"Subclass of {edge.base_qualified_name or edge.base_name}",
        confidence=min(resolution_confidence, RESOLVED_CONFIDENCE),
    )
