import pytest

from codebase_agent.chunking.models import CodeChunk
from codebase_agent.embeddings import CodeEmbedder
from codebase_agent.graph.retrieve import retrieve
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


def _state(strategy: str, symbol: str | None = None, question: str = "") -> dict:
    return {
        "repo_name": "test-repo",
        "question": question,
        "retrieval_strategy": strategy,
        "target_symbol": symbol,
        "retrieved_chunks": [],
        "answer": None,
    }


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
    ]
    s.rebuild_repo_collection("test-repo", chunks, [[1.0, 0.0], [0.0, 1.0]])
    return s


def test_dispatches_to_find_by_qualified_name(store):
    retriever = CodeRetriever(embedder=None, store=store)
    result = retrieve(
        retriever, _state("find_by_qualified_name", symbol="validate_refund")
    )
    assert [c.qualified_name for c in result["retrieved_chunks"]] == ["validate_refund"]


def test_dispatches_to_find_references(store):
    retriever = CodeRetriever(embedder=None, store=store)
    result = retrieve(retriever, _state("find_references", symbol="validate_refund"))
    assert {c.qualified_name for c in result["retrieved_chunks"]} == {
        "validate_refund",
        "process_order",
    }


@pytest.fixture
def embedded_store(tmp_path):
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
def test_dispatches_to_semantic_search(embedded_store):
    store, embedder = embedded_store
    retriever = CodeRetriever(embedder=embedder, store=store)
    result = retrieve(
        retriever,
        _state(
            "semantic_search", question="how do we check if a refund amount is valid"
        ),
    )
    assert result["retrieved_chunks"][0].qualified_name == "validate_refund"
