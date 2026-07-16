import logging

from codebase_agent.intelligence.models import ImportEdge
from codebase_agent.knowledge import KnowledgeBase
from codebase_agent.retrieval.evidence import EvidenceItem, EvidenceSource
from codebase_agent.retrieval.plan import RetrievalStep
from codebase_agent.retrieval.retrievers.resolution import (
    RESOLVED_CONFIDENCE,
    UNRESOLVED_CONFIDENCE,
    resolve_file_path,
)

logger = logging.getLogger(__name__)


class ImportRetriever:
    """What a file depends on, and/or what depends on it - dependency analysis."""

    def retrieve(self, kb: KnowledgeBase, step: RetrievalStep) -> list[EvidenceItem]:
        if not step.target:
            logger.warning("import_graph step has no target - skipping")
            return []

        file_path = resolve_file_path(kb, step.target)
        if file_path is None:
            return []

        direction = (
            step.direction if step.direction in ("imports", "importers") else "both"
        )
        items = []
        if direction in ("imports", "both"):
            items.extend(_imports_item(edge) for edge in kb.imports_of(file_path))
        if direction in ("importers", "both"):
            items.extend(_importers_item(edge) for edge in kb.importers_of(file_path))
        return items


def _imports_item(edge: ImportEdge) -> EvidenceItem:
    resolved = edge.resolved_file is not None
    explanation = f"{edge.importer_file} imports {edge.imported_module}"
    if not resolved:
        explanation += " (external, not part of this repo)"
    return EvidenceItem(
        source=EvidenceSource.IMPORT_GRAPH,
        qualified_name=None,
        file_path=edge.resolved_file or edge.importer_file,
        start_line=None,
        end_line=None,
        content=explanation,
        explanation=explanation,
        confidence=RESOLVED_CONFIDENCE if resolved else UNRESOLVED_CONFIDENCE,
    )


def _importers_item(edge: ImportEdge) -> EvidenceItem:
    explanation = f"{edge.importer_file} imports this file"
    return EvidenceItem(
        source=EvidenceSource.IMPORT_GRAPH,
        qualified_name=None,
        file_path=edge.importer_file,
        start_line=None,
        end_line=None,
        content=explanation,
        explanation=explanation,
        # importers_of only ever returns edges already resolved to this file.
        confidence=RESOLVED_CONFIDENCE,
    )
