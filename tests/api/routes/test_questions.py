from unittest.mock import Mock

from fastapi.testclient import TestClient

from codebase_agent.api.app import create_app
from codebase_agent.api.dependencies import get_reasoning_service
from codebase_agent.reasoning import AnswerConfidence, ReasoningResult
from codebase_agent.retrieval.evidence import EvidenceBundle
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)


def _result() -> ReasoningResult:
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH),)
    )
    bundle = EvidenceBundle(
        question="q",
        plan=plan,
        items=(),
        retrievers_used=(),
        warnings=(),
        execution_time_seconds=0.0,
    )
    return ReasoningResult(
        question="q",
        answer="the answer",
        confidence=AnswerConfidence.HIGH,
        evidence_sufficient=True,
        assumptions=(),
        limitations=(),
        citations=(),
        cited_evidence_indices=(),
        validation_issues=(),
        evidence_bundle=bundle,
        model="m",
        prompt_version="v1",
        reasoning_time_seconds=0.1,
    )


def test_ask_question():
    app = create_app()
    service = Mock()
    service.answer_question.return_value = _result()
    app.dependency_overrides[get_reasoning_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(
            "/v1/repositories/repo/questions", json={"question": "what does this do?"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "the answer"
    assert body["confidence"] == "high"
    service.answer_question.assert_called_once_with(
        "repo", "what does this do?", active_file=None, active_symbol=None
    )


def test_ask_question_with_context():
    app = create_app()
    service = Mock()
    service.answer_question.return_value = _result()
    app.dependency_overrides[get_reasoning_service] = lambda: service

    with TestClient(app) as client:
        client.post(
            "/v1/repositories/repo/questions",
            json={"question": "q", "active_file": "a.py", "active_symbol": "foo"},
        )

    service.answer_question.assert_called_once_with(
        "repo", "q", active_file="a.py", active_symbol="foo"
    )
