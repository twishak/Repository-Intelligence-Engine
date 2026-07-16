from unittest.mock import Mock

import pytest

from codebase_agent.application.errors import RepositoryNotFoundError
from codebase_agent.application.services.reasoning_service import ReasoningService
from codebase_agent.knowledge import RepoNotIngestedError
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)


def test_answer_question_returns_result_from_pipeline():
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
    kb_registry.get.return_value = Mock()

    service = ReasoningService(
        planner=planner, executor=executor, engine=engine, kb_registry=kb_registry
    )

    result = service.answer_question("repo", "question")

    assert result is reasoning_result
    planner.plan.assert_called_once_with("question", context=None)


def test_raises_repository_not_found_before_running_the_pipeline():
    kb_registry = Mock()
    kb_registry.get.side_effect = RepoNotIngestedError("repo")

    service = ReasoningService(
        planner=Mock(), executor=Mock(), engine=Mock(), kb_registry=kb_registry
    )

    with pytest.raises(RepositoryNotFoundError):
        service.answer_question("repo", "question")


def test_builds_retrieval_context_from_active_file_and_symbol():
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
    engine.reason.return_value = Mock()
    kb_registry = Mock()
    kb_registry.get.return_value = Mock()

    service = ReasoningService(
        planner=planner, executor=executor, engine=engine, kb_registry=kb_registry
    )
    service.answer_question(
        "repo", "question", active_file="pkg/a.py", active_symbol="foo"
    )

    _, kwargs = planner.plan.call_args
    context = kwargs["context"]
    assert context.active_file == "pkg/a.py"
    assert context.active_symbol == "foo"
    assert context.repo_name == "repo"
