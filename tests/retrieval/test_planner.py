import json

import pytest

from codebase_agent.retrieval.plan import RetrievalPriority, RetrievalStrategy
from codebase_agent.retrieval.planner import RetrievalContext, RetrievalPlanner


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


def _tool_call_message(**arguments) -> _FakeMessage:
    return _FakeMessage(
        tool_calls=[_FakeToolCall("build_retrieval_plan", json.dumps(arguments))]
    )


def test_parses_single_step_plan():
    llm = _FakeLLM(
        _tool_call_message(
            intent="symbol_lookup",
            steps=[{"strategy": "symbol_lookup", "target": "AuthService.login"}],
        )
    )

    plan = RetrievalPlanner(llm=llm).plan("explain AuthService.login")

    assert plan.intent == "symbol_lookup"
    assert len(plan.steps) == 1
    assert plan.steps[0].strategy == RetrievalStrategy.SYMBOL_LOOKUP
    assert plan.steps[0].target == "AuthService.login"
    assert plan.priority == RetrievalPriority.NORMAL


def test_plans_at_zero_temperature_for_deterministic_strategy_choice():
    # Regression test: without a fixed temperature, the same question could
    # get routed to a different (sometimes wrong, e.g. a hallucinated
    # symbol name) retrieval strategy from one call to the next.
    llm = _FakeLLM(
        _tool_call_message(
            intent="symbol_lookup",
            steps=[{"strategy": "symbol_lookup", "target": "AuthService.login"}],
        )
    )

    RetrievalPlanner(llm=llm).plan("explain AuthService.login")

    assert llm.last_kwargs["temperature"] == 0


def test_parses_multi_step_plan_for_impact_analysis():
    llm = _FakeLLM(
        _tool_call_message(
            intent="impact_analysis",
            steps=[
                {"strategy": "symbol_lookup", "target": "login"},
                {"strategy": "call_graph", "target": "login", "direction": "callers"},
            ],
        )
    )

    plan = RetrievalPlanner(llm=llm).plan("what would break if I changed login?")

    assert [s.strategy for s in plan.steps] == [
        RetrievalStrategy.SYMBOL_LOOKUP,
        RetrievalStrategy.CALL_GRAPH,
    ]
    assert plan.steps[1].direction == "callers"


def test_parses_max_results():
    llm = _FakeLLM(
        _tool_call_message(steps=[{"strategy": "semantic_search"}], max_results=3)
    )

    plan = RetrievalPlanner(llm=llm).plan("q")

    assert plan.max_results == 3


def test_ignores_invalid_max_results():
    llm = _FakeLLM(
        _tool_call_message(steps=[{"strategy": "semantic_search"}], max_results=-1)
    )

    plan = RetrievalPlanner(llm=llm).plan("q")

    assert plan.max_results is None


def test_drops_step_with_unknown_strategy():
    llm = _FakeLLM(
        _tool_call_message(
            steps=[{"strategy": "bogus"}, {"strategy": "semantic_search"}]
        )
    )

    plan = RetrievalPlanner(llm=llm).plan("q")

    assert [s.strategy for s in plan.steps] == [RetrievalStrategy.SEMANTIC_SEARCH]


def test_normalizes_unrecognized_direction_to_none():
    llm = _FakeLLM(
        _tool_call_message(
            steps=[{"strategy": "call_graph", "target": "x", "direction": "sideways"}]
        )
    )

    plan = RetrievalPlanner(llm=llm).plan("q")

    assert plan.steps[0].direction is None


def test_falls_back_to_semantic_search_when_no_tool_call_returned():
    llm = _FakeLLM(_FakeMessage(tool_calls=None))

    plan = RetrievalPlanner(llm=llm).plan("where is login handled?")

    assert plan.intent == "fallback"
    assert len(plan.steps) == 1
    assert plan.steps[0].strategy == RetrievalStrategy.SEMANTIC_SEARCH
    assert plan.steps[0].query == "where is login handled?"


def test_falls_back_when_all_steps_invalid():
    llm = _FakeLLM(_tool_call_message(steps=[{"strategy": "bogus"}]))

    plan = RetrievalPlanner(llm=llm).plan("q")

    assert plan.intent == "fallback"


def test_forces_the_planner_tool_choice():
    llm = _FakeLLM(_tool_call_message(steps=[{"strategy": "semantic_search"}]))

    RetrievalPlanner(llm=llm).plan("q")

    assert llm.last_kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "build_retrieval_plan"},
    }


def test_context_adds_grounding_hint_to_prompt():
    llm = _FakeLLM(_tool_call_message(steps=[{"strategy": "semantic_search"}]))
    context = RetrievalContext(
        repo_name="repo", active_file="pkg/auth.py", active_symbol="AuthService.login"
    )

    RetrievalPlanner(llm=llm).plan("what does this call?", context=context)

    user_message = llm.last_kwargs["messages"][1]["content"]
    assert "AuthService.login" in user_message
    assert "pkg/auth.py" in user_message


def test_context_without_active_fields_leaves_prompt_unchanged():
    llm = _FakeLLM(_tool_call_message(steps=[{"strategy": "semantic_search"}]))
    context = RetrievalContext(repo_name="repo")

    RetrievalPlanner(llm=llm).plan("q", context=context)

    assert llm.last_kwargs["messages"][1]["content"] == "q"


@pytest.mark.integration
def test_extracts_bare_identifier_not_descriptive_phrase():
    # Regression test: "what does the option decorator do" against a real
    # planner call used to produce target='option decorator' - the whole
    # descriptive phrase from the question - instead of the actual
    # identifier 'option', so it could never resolve to a real symbol no
    # matter how permissive symbol resolution became.
    plan = RetrievalPlanner().plan("what does the option decorator do")

    targets = [step.target for step in plan.steps if step.target]
    assert targets, "expected at least one step with a target"
    for target in targets:
        assert " " not in target, (
            f"target {target!r} looks like a phrase, not an identifier"
        )
    assert "option" in targets


@pytest.mark.integration
def test_extracts_bare_identifier_for_a_class_method_phrase():
    plan = RetrievalPlanner().plan("what does the login method on AuthService do")

    targets = [step.target for step in plan.steps if step.target]
    assert targets, "expected at least one step with a target"
    for target in targets:
        assert " " not in target, (
            f"target {target!r} looks like a phrase, not an identifier"
        )
