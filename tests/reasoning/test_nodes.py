from unittest.mock import Mock

from codebase_agent.reasoning.nodes import execute_retrieval, plan_retrieval, reason
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)


def test_plan_retrieval_calls_planner_with_question_and_context():
    planner = Mock()
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH),)
    )
    planner.plan.return_value = plan
    state = {"question": "q", "context": None}

    result = plan_retrieval(planner, state)

    planner.plan.assert_called_once_with("q", context=None)
    assert result == {"plan": plan}


def test_execute_retrieval_uses_kb_from_registry():
    executor = Mock()
    kb_registry = Mock()
    kb = Mock()
    kb_registry.get.return_value = kb
    bundle = Mock()
    bundle.__len__ = Mock(return_value=0)
    executor.execute.return_value = bundle
    plan = RetrievalPlan(steps=())
    state = {"repo_name": "repo", "question": "q", "plan": plan}

    result = execute_retrieval(executor, kb_registry, state)

    kb_registry.get.assert_called_once_with("repo")
    executor.execute.assert_called_once_with(kb, "q", plan)
    assert result == {"evidence": bundle}


def test_reason_calls_engine_with_evidence():
    engine = Mock()
    reasoning_result = Mock()
    engine.reason.return_value = reasoning_result
    evidence = Mock()
    state = {"evidence": evidence}

    result = reason(engine, state)

    engine.reason.assert_called_once_with(evidence)
    assert result == {"result": reasoning_result}
