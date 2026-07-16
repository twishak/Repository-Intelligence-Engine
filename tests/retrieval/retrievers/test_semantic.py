from unittest.mock import Mock

from codebase_agent.retrieval.plan import RetrievalStep, RetrievalStrategy
from codebase_agent.retrieval.retrievers.semantic import SemanticRetriever
from codebase_agent.storage.models import RetrievedChunk


def _chunk(distance: float | None = 0.2) -> RetrievedChunk:
    return RetrievedChunk(
        id="x",
        file_path="pkg/a.py",
        chunk_type="function",
        qualified_name="pkg.a.foo",
        start_line=1,
        end_line=2,
        content="def foo(): ...",
        docstring=None,
        distance=distance,
    )


def test_maps_chunks_to_evidence_with_confidence():
    kb = Mock()
    kb.semantic_search.return_value = [_chunk(distance=0.2)]
    step = RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="find foo")

    items = SemanticRetriever().retrieve(kb, step)

    kb.semantic_search.assert_called_once_with("find foo", k=8)
    assert len(items) == 1
    assert items[0].confidence == 0.8
    assert items[0].content == "def foo(): ..."


def test_falls_back_to_target_when_no_query():
    kb = Mock()
    kb.semantic_search.return_value = []
    step = RetrievalStep(
        strategy=RetrievalStrategy.SEMANTIC_SEARCH, target="fallback text"
    )

    SemanticRetriever().retrieve(kb, step)

    kb.semantic_search.assert_called_once_with("fallback text", k=8)


def test_no_query_or_target_returns_empty():
    kb = Mock()
    step = RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH)

    assert SemanticRetriever().retrieve(kb, step) == []
    kb.semantic_search.assert_not_called()


def test_confidence_clamped_at_zero_for_large_distance():
    kb = Mock()
    kb.semantic_search.return_value = [_chunk(distance=1.5)]
    step = RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="q")

    items = SemanticRetriever().retrieve(kb, step)

    assert items[0].confidence == 0.0


def test_none_distance_yields_none_confidence():
    kb = Mock()
    kb.semantic_search.return_value = [_chunk(distance=None)]
    step = RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="q")

    items = SemanticRetriever().retrieve(kb, step)

    assert items[0].confidence is None
