import json

import pytest

from codebase_agent.chunking.models import CodeChunk
from codebase_agent.graph.pipeline import answer_question
from codebase_agent.retrieval import CodeRetriever
from codebase_agent.storage import CodeVectorStore


class _FakeToolCall:
    def __init__(self, name, arguments):
        self.function = _FakeFunction(name, arguments)


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeLLM:
    """Always routes to find_by_qualified_name for `_symbol`, then grounds the
    final answer on whatever context it's handed."""

    def __init__(self, symbol: str):
        self._symbol = symbol

    def chat(self, messages, tools=None, tool_choice=None):
        if tools:
            args = json.dumps(
                {"strategy": "find_by_qualified_name", "symbol": self._symbol}
            )
            return _FakeMessage(
                tool_calls=[_FakeToolCall("select_retrieval_strategy", args)]
            )

        context = messages[1]["content"]
        if "no matching code found" in context:
            return _FakeMessage(content="insufficient context")
        return _FakeMessage(content="found it")


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
def retriever(tmp_path):
    store = CodeVectorStore(persist_dir=tmp_path)
    chunks = [
        _chunk(
            "validate_refund",
            content="def validate_refund(refund):\n    return refund.amount > 0",
        )
    ]
    store.rebuild_repo_collection("test-repo", chunks, [[1.0, 0.0]])
    return CodeRetriever(embedder=None, store=store)


def test_pipeline_routes_retrieves_and_answers(retriever):
    answer = answer_question(
        "test-repo",
        "explain validate_refund",
        llm=_FakeLLM("validate_refund"),
        retriever=retriever,
    )
    assert answer == "found it"


def test_pipeline_reports_insufficient_context_when_symbol_not_found(retriever):
    answer = answer_question(
        "test-repo",
        "explain does_not_exist",
        llm=_FakeLLM("does_not_exist"),
        retriever=retriever,
    )
    assert answer == "insufficient context"
