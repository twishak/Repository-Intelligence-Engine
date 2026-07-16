import logging

from codebase_agent.knowledge import KnowledgeBase
from codebase_agent.retrieval.evidence import EvidenceItem, EvidenceSource
from codebase_agent.retrieval.plan import RetrievalStep
from codebase_agent.retrieval.retrievers.resolution import (
    RESOLVED_CONFIDENCE,
    resolve_symbol_candidates,
)

logger = logging.getLogger(__name__)


class SymbolRetriever:
    """Resolves a step's target to one or more known symbols, exact qualified
    name preferred, unambiguous short name as a fallback.
    """

    def retrieve(self, kb: KnowledgeBase, step: RetrievalStep) -> list[EvidenceItem]:
        if not step.target:
            logger.warning("symbol_lookup step has no target - skipping")
            return []

        candidates = resolve_symbol_candidates(kb, step.target)
        items = []
        for symbol, confidence in candidates:
            content = kb.get_source(symbol.qualified_name) or symbol.signature
            if confidence == RESOLVED_CONFIDENCE:
                explanation = f"Exact match for '{step.target}'"
            else:
                explanation = (
                    f"Possible match for '{step.target}' (ambiguous short name, "
                    f"{len(candidates)} candidates)"
                )
            items.append(
                EvidenceItem(
                    source=EvidenceSource.SYMBOL,
                    qualified_name=symbol.qualified_name,
                    file_path=symbol.file_path,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    content=content,
                    explanation=explanation,
                    confidence=confidence,
                )
            )
        return items
