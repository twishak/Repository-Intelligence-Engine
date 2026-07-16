import json

from codebase_agent.reasoning.engine import ReasoningEngine
from codebase_agent.reasoning.result import AnswerConfidence
from codebase_agent.retrieval.evidence import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceSource,
)
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)


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
    model = "fake-model"

    def __init__(self, message):
        self._message = message
        self.last_kwargs = None

    def chat(self, **kwargs):
        self.last_kwargs = kwargs
        return self._message


def _tool_call_message(**arguments) -> _FakeMessage:
    return _FakeMessage(
        tool_calls=[_FakeToolCall("submit_reasoning_result", json.dumps(arguments))]
    )


def _item() -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.SYMBOL,
        qualified_name="pkg.a.foo",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        content="def foo(): ...",
        explanation="Exact match",
        confidence=1.0,
    )


def _bundle(items: list[EvidenceItem]) -> EvidenceBundle:
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="foo"),)
    )
    return EvidenceBundle(
        question="what does foo do?",
        plan=plan,
        items=tuple(items),
        retrievers_used=(RetrievalStrategy.SYMBOL_LOOKUP,),
        warnings=(),
        execution_time_seconds=0.01,
    )


def test_resolves_valid_citation_to_exact_evidence_location():
    llm = _FakeLLM(
        _tool_call_message(
            answer="foo does X [1]",
            citations=[1],
            confidence="high",
            evidence_sufficient=True,
        )
    )
    bundle = _bundle([_item()])

    result = ReasoningEngine(llm=llm).reason(bundle)

    assert result.confidence == AnswerConfidence.HIGH
    assert result.evidence_sufficient is True
    assert len(result.citations) == 1
    assert result.citations[0].file_path == "pkg/a.py"
    assert result.citations[0].start_line == 1
    assert result.model == "fake-model"


def test_out_of_range_citation_is_dropped_from_citations_but_kept_in_raw_indices():
    llm = _FakeLLM(
        _tool_call_message(
            answer="foo does X [1] [7]",
            citations=[1, 7],
            confidence="medium",
            evidence_sufficient=True,
        )
    )
    bundle = _bundle([_item()])

    result = ReasoningEngine(llm=llm).reason(bundle)

    assert result.cited_evidence_indices == (1, 7)
    assert [c.evidence_index for c in result.citations] == [1]
    assert any(
        "does not correspond" in issue.message for issue in result.validation_issues
    )


def test_captures_assumptions_and_limitations():
    llm = _FakeLLM(
        _tool_call_message(
            answer="...",
            citations=[],
            confidence="low",
            evidence_sufficient=False,
            assumptions=["assumes default config"],
            limitations=["only symbol lookup evidence available"],
        )
    )
    bundle = _bundle([_item()])

    result = ReasoningEngine(llm=llm).reason(bundle)

    assert result.assumptions == ("assumes default config",)
    assert result.limitations == ("only symbol lookup evidence available",)


def test_falls_back_when_no_tool_call_returned():
    llm = _FakeLLM(_FakeMessage(tool_calls=None))
    bundle = _bundle([])

    result = ReasoningEngine(llm=llm).reason(bundle)

    assert result.confidence == AnswerConfidence.LOW
    assert result.evidence_sufficient is False
    assert result.citations == ()


def test_unknown_confidence_value_defaults_to_low():
    llm = _FakeLLM(
        _tool_call_message(
            answer="...",
            citations=[],
            confidence="extremely-sure",
            evidence_sufficient=False,
        )
    )
    bundle = _bundle([])

    result = ReasoningEngine(llm=llm).reason(bundle)

    assert result.confidence == AnswerConfidence.LOW


def test_forces_the_reasoning_tool_choice():
    llm = _FakeLLM(
        _tool_call_message(
            answer="...", citations=[], confidence="low", evidence_sufficient=False
        )
    )
    bundle = _bundle([])

    ReasoningEngine(llm=llm).reason(bundle)

    assert llm.last_kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "submit_reasoning_result"},
    }


def test_reasoning_time_and_prompt_version_are_recorded():
    llm = _FakeLLM(
        _tool_call_message(
            answer="...", citations=[], confidence="low", evidence_sufficient=False
        )
    )
    bundle = _bundle([])

    result = ReasoningEngine(llm=llm).reason(bundle)

    assert result.reasoning_time_seconds >= 0
    assert result.prompt_version
