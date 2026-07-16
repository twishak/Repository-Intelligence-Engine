from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalPriority,
    RetrievalStep,
    RetrievalStrategy,
)


def test_step_defaults():
    step = RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH)

    assert step.target is None
    assert step.query is None
    assert step.direction is None


def test_plan_defaults():
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="foo"),)
    )

    assert plan.intent is None
    assert plan.priority == RetrievalPriority.NORMAL
    assert plan.max_results is None
