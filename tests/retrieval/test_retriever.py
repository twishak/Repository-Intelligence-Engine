import pytest

from codebase_agent.chunking.models import CodeChunk
from codebase_agent.embeddings import CodeEmbedder
from codebase_agent.retrieval import CodeRetriever
from codebase_agent.storage import CodeVectorStore


def _chunk(qualified_name: str, content: str | None = None) -> CodeChunk:
    return CodeChunk(
        id=f"a.py::function::{qualified_name}",
        file_path="a.py",
        chunk_type="function",
        qualified_name=qualified_name,
        start_line=1,
        end_line=2,
        content=content or f"def {qualified_name}(): pass",
        docstring=None,
    )


@pytest.fixture
def store(tmp_path):
    s = CodeVectorStore(persist_dir=tmp_path)
    chunks = [
        _chunk(
            "validate_refund",
            content="def validate_refund(refund):\n    return refund.amount > 0",
        ),
        _chunk(
            "process_order", content="def process_order():\n    validate_refund(order)"
        ),
        _chunk("unrelated", content="def unrelated():\n    return 42"),
    ]
    s.rebuild_repo_collection("test-repo", chunks, [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
    return s


def test_find_by_qualified_name_does_not_touch_embedder(store):
    retriever = CodeRetriever(embedder=None, store=store)
    results = retriever.find_by_qualified_name("test-repo", "validate_refund")

    assert [r.qualified_name for r in results] == ["validate_refund"]
    # No embedding model should have been loaded for a pure metadata lookup.
    assert retriever._embedder._model is None


def test_find_references_does_not_touch_embedder(store):
    retriever = CodeRetriever(embedder=None, store=store)
    results = retriever.find_references("test-repo", "validate_refund")

    assert {r.qualified_name for r in results} == {"validate_refund", "process_order"}
    assert retriever._embedder._model is None


@pytest.fixture
def embedded_store(tmp_path):
    # Semantic search needs real (768-dim) embeddings, unlike the fake 2-dim
    # vectors the `store` fixture above uses for the lexical/metadata tests.
    s = CodeVectorStore(persist_dir=tmp_path)
    chunks = [
        _chunk(
            "validate_refund",
            content="def validate_refund(refund):\n    return refund.amount > 0",
        ),
        _chunk("unrelated", content="def unrelated():\n    return 42"),
    ]
    embedder = CodeEmbedder()
    vectors = embedder.embed([c.content for c in chunks])
    s.rebuild_repo_collection("test-repo", chunks, vectors)
    return s, embedder


@pytest.mark.integration
def test_semantic_search_uses_real_embeddings(embedded_store):
    store, embedder = embedded_store
    retriever = CodeRetriever(embedder=embedder, store=store)
    results = retriever.semantic_search(
        "test-repo", "how do we check if a refund amount is valid", k=1
    )

    assert results[0].qualified_name == "validate_refund"
    assert results[0].distance is not None
