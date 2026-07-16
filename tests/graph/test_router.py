import json

from codebase_agent.graph.router import route_question


class _FakeToolCall:
    def __init__(self, name, arguments):
        self.function = _FakeFunction(name, arguments)


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _FakeMessage:
    def __init__(self, tool_calls=None):
        self.tool_calls = tool_calls
        self.content = None


class _FakeLLM:
    def __init__(self, message):
        self._message = message
        self.last_kwargs = None

    def chat(self, **kwargs):
        self.last_kwargs = kwargs
        return self._message


def _tool_call_message(strategy, symbol=None):
    args = {"strategy": strategy}
    if symbol is not None:
        args["symbol"] = symbol
    return _FakeMessage(
        tool_calls=[_FakeToolCall("select_retrieval_strategy", json.dumps(args))]
    )


def _state(question="how are refunds validated?"):
    return {
        "repo_name": "repo",
        "question": question,
        "retrieval_strategy": "",
        "target_symbol": None,
        "retrieved_chunks": [],
        "answer": None,
    }


def test_routes_to_semantic_search():
    llm = _FakeLLM(_tool_call_message("semantic_search"))
    result = route_question(llm, _state())
    assert result == {"retrieval_strategy": "semantic_search", "target_symbol": None}


def test_routes_to_find_by_qualified_name_with_symbol():
    llm = _FakeLLM(
        _tool_call_message("find_by_qualified_name", symbol="validate_refund")
    )
    result = route_question(llm, _state())
    assert result == {
        "retrieval_strategy": "find_by_qualified_name",
        "target_symbol": "validate_refund",
    }


def test_falls_back_to_semantic_search_when_symbol_missing_for_exact_strategy():
    llm = _FakeLLM(_tool_call_message("find_references"))  # no symbol supplied
    result = route_question(llm, _state())
    assert result == {"retrieval_strategy": "semantic_search", "target_symbol": None}


def test_falls_back_to_semantic_search_when_no_tool_call_returned():
    llm = _FakeLLM(_FakeMessage(tool_calls=None))
    result = route_question(llm, _state())
    assert result == {"retrieval_strategy": "semantic_search", "target_symbol": None}


def test_forces_the_router_tool_choice():
    llm = _FakeLLM(_tool_call_message("semantic_search"))
    route_question(llm, _state())
    assert llm.last_kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "select_retrieval_strategy"},
    }
