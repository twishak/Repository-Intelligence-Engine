from codebase_agent.chunking.models import CodeChunk
from codebase_agent.storage import CodeVectorStore


def _chunk(
    qualified_name: str, docstring: str | None = None, content: str | None = None
) -> CodeChunk:
    return CodeChunk(
        id=f"a.py::function::{qualified_name}",
        file_path="a.py",
        chunk_type="function",
        qualified_name=qualified_name,
        start_line=1,
        end_line=2,
        content=content or f"def {qualified_name}(): pass",
        docstring=docstring,
    )


def test_query_returns_closest_match_first(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    chunks = [_chunk("foo"), _chunk("bar")]
    vectors = [[1.0, 0.0], [0.0, 1.0]]

    store.rebuild_repo_collection("test-repo", chunks, vectors)
    results = store.query("test-repo", query_vector=[0.9, 0.1], n_results=2)

    assert [r.qualified_name for r in results] == ["foo", "bar"]
    assert results[0].distance < results[1].distance


def test_missing_docstring_round_trips_as_none(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    chunks = [_chunk("foo", docstring=None), _chunk("bar", docstring="does bar things")]
    vectors = [[1.0, 0.0], [0.0, 1.0]]

    store.rebuild_repo_collection("test-repo", chunks, vectors)
    results = store.query("test-repo", query_vector=[1.0, 0.0], n_results=2)

    by_name = {r.qualified_name: r for r in results}
    assert by_name["foo"].docstring is None
    assert by_name["bar"].docstring == "does bar things"


def test_rebuild_replaces_removed_chunks(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    store.rebuild_repo_collection(
        "test-repo", [_chunk("foo"), _chunk("bar")], [[1.0, 0.0], [0.0, 1.0]]
    )

    # Simulate re-ingestion after `bar` was deleted from the source file.
    store.rebuild_repo_collection("test-repo", [_chunk("foo")], [[1.0, 0.0]])
    results = store.query("test-repo", query_vector=[0.0, 1.0], n_results=2)

    assert [r.qualified_name for r in results] == ["foo"]


def test_collection_name_survives_unusual_repo_names(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    store.rebuild_repo_collection("My Repo!@# (fork)", [_chunk("foo")], [[1.0, 0.0]])
    results = store.query("My Repo!@# (fork)", query_vector=[1.0, 0.0], n_results=1)

    assert [r.qualified_name for r in results] == ["foo"]


def test_get_by_qualified_name_returns_exact_match_only(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    chunks = [_chunk("PaymentHandler.handle_refund"), _chunk("PaymentHandler.validate")]
    store.rebuild_repo_collection("test-repo", chunks, [[1.0, 0.0], [0.0, 1.0]])

    results = store.get_by_qualified_name("test-repo", "PaymentHandler.handle_refund")

    assert [r.qualified_name for r in results] == ["PaymentHandler.handle_refund"]
    assert results[0].distance is None


def test_search_document_text_finds_literal_references(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    chunks = [
        _chunk(
            "process_order", content="def process_order():\n    validate_refund(order)"
        ),
        _chunk("unrelated", content="def unrelated():\n    return 42"),
    ]
    store.rebuild_repo_collection("test-repo", chunks, [[1.0, 0.0], [0.0, 1.0]])

    results = store.search_document_text("test-repo", "validate_refund")

    assert [r.qualified_name for r in results] == ["process_order"]
    assert results[0].distance is None


def test_has_collection_reflects_ingestion_state(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    assert store.has_collection("test-repo") is False

    store.rebuild_repo_collection("test-repo", [_chunk("foo")], [[1.0, 0.0]])
    assert store.has_collection("test-repo") is True


def test_list_repos_returns_ingested_collection_names(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    store.rebuild_repo_collection("repo-a", [_chunk("foo")], [[1.0, 0.0]])
    store.rebuild_repo_collection("repo-b", [_chunk("foo")], [[1.0, 0.0]])

    assert store.list_repos() == ["repo-a", "repo-b"]
