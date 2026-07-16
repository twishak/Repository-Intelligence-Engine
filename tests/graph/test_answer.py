from codebase_agent.graph.answer import generate_answer
from codebase_agent.storage.models import RetrievedChunk


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    def __init__(self, content):
        self._content = content
        self.last_kwargs = None

    def chat(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeMessage(self._content)


def _state(chunks: list[RetrievedChunk]) -> dict:
    return {
        "repo_name": "repo",
        "question": "how are refunds validated?",
        "retrieval_strategy": "semantic_search",
        "target_symbol": None,
        "retrieved_chunks": chunks,
        "answer": None,
    }


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="a.py::function::validate_refund",
        file_path="a.py",
        chunk_type="function",
        qualified_name="validate_refund",
        start_line=1,
        end_line=2,
        content="def validate_refund(refund):\n    return refund.amount > 0",
        docstring=None,
        distance=0.1,
    )


def test_returns_llm_answer_and_includes_chunk_citations_in_prompt():
    llm = _FakeLLM("Refunds are validated in `a.py:1-2`.")
    result = generate_answer(llm, _state([_chunk()]))

    assert result == {"answer": "Refunds are validated in `a.py:1-2`."}
    user_message = llm.last_kwargs["messages"][1]["content"]
    assert "a.py:1-2" in user_message
    assert "validate_refund" in user_message


def test_tells_the_model_when_no_context_was_found():
    llm = _FakeLLM("I don't have enough context to answer that.")
    generate_answer(llm, _state([]))

    user_message = llm.last_kwargs["messages"][1]["content"]
    assert "no matching code found" in user_message
