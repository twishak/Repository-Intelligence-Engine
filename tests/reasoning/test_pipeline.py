from unittest.mock import Mock

from codebase_agent.reasoning.pipeline import answer_question, build_reasoning_pipeline
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)


def test_answer_question_wires_planner_executor_and_engine_in_order():
    planner = Mock()
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH),)
    )
    planner.plan.return_value = plan

    executor = Mock()
    evidence = Mock()
    evidence.__len__ = Mock(return_value=0)
    executor.execute.return_value = evidence

    engine = Mock()
    reasoning_result = Mock()
    engine.reason.return_value = reasoning_result

    kb_registry = Mock()
    kb = Mock()
    kb_registry.get.return_value = kb

    result = answer_question(
        "repo",
        "question",
        planner=planner,
        executor=executor,
        engine=engine,
        kb_registry=kb_registry,
    )

    planner.plan.assert_called_once_with("question", context=None)
    kb_registry.get.assert_called_once_with("repo")
    executor.execute.assert_called_once_with(kb, "question", plan)
    engine.reason.assert_called_once_with(evidence)
    assert result is reasoning_result


def test_build_reasoning_pipeline_compiles():
    pipeline = build_reasoning_pipeline(
        planner=Mock(), executor=Mock(), engine=Mock(), kb_registry=Mock()
    )

    assert pipeline is not None
