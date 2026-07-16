import logging

from codebase_agent.knowledge import KnowledgeBase
from codebase_agent.retrieval.evidence import EvidenceItem, EvidenceSource
from codebase_agent.retrieval.plan import RetrievalStep

logger = logging.getLogger(__name__)

_DEFAULT_K = 8


class SemanticRetriever:
    """Embedding similarity search over the repo's indexed chunks.

    Confidence is `max(0, 1 - distance)` - a rough heuristic derived from
    cosine distance in a normalized embedding space, not a calibrated
    probability. Useful for ranking within this retriever's own results, not
    for comparing against other sources' confidence values.
    """

    def retrieve(self, kb: KnowledgeBase, step: RetrievalStep) -> list[EvidenceItem]:
        query = step.query or step.target
        if not query:
            logger.warning("semantic_search step has no query - skipping")
            return []

        chunks = kb.semantic_search(query, k=_DEFAULT_K)
        items = []
        for chunk in chunks:
            if chunk.distance is not None:
                confidence = max(0.0, 1.0 - chunk.distance)
                explanation = (
                    f"Semantically similar to '{query}' (distance {chunk.distance:.3f})"
                )
            else:
                confidence = None
                explanation = f"Matched query '{query}'"
            items.append(
                EvidenceItem(
                    source=EvidenceSource.SEMANTIC,
                    qualified_name=chunk.qualified_name,
                    file_path=chunk.file_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    content=chunk.content,
                    explanation=explanation,
                    confidence=confidence,
                )
            )
        return items
