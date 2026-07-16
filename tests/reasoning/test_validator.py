from codebase_agent.reasoning.result import (
    AnswerConfidence,
    ReasoningResult,
    ValidationSeverity,
)
from codebase_agent.reasoning.validator import AnswerValidator
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


def _item() -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.SYMBOL,
        qualified_name="pkg.a.foo",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        content="...",
        explanation="...",
        confidence=1.0,
    )


def _bundle(items: list[EvidenceItem]) -> EvidenceBundle:
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="foo"),)
    )
    return EvidenceBundle(
        question="q",
        plan=plan,
        items=tuple(items),
        retrievers_used=(),
        warnings=(),
        execution_time_seconds=0.0,
    )


def _result(evidence_bundle: EvidenceBundle, **overrides) -> ReasoningResult:
    defaults = dict(
        question="q",
        answer="an answer",
        confidence=AnswerConfidence.HIGH,
        evidence_sufficient=True,
        assumptions=(),
        limitations=(),
        citations=(),
        cited_evidence_indices=(),
        validation_issues=(),
        evidence_bundle=evidence_bundle,
        model="m",
        prompt_version="v1",
        reasoning_time_seconds=0.0,
    )
    defaults.update(overrides)
    return ReasoningResult(**defaults)


def test_no_issues_for_a_well_formed_result():
    bundle = _bundle([_item()])
    result = _result(bundle, cited_evidence_indices=(1,))

    assert AnswerValidator().validate(result, bundle) == []


def test_flags_out_of_range_citation():
    bundle = _bundle([_item()])
    result = _result(bundle, cited_evidence_indices=(1, 5))

    issues = AnswerValidator().validate(result, bundle)

    assert any(
        i.severity == ValidationSeverity.ERROR and "5" in i.message for i in issues
    )


def test_flags_sufficient_claim_with_no_evidence():
    bundle = _bundle([])
    result = _result(bundle, evidence_sufficient=True, cited_evidence_indices=())

    issues = AnswerValidator().validate(result, bundle)

    assert any("no evidence was retrieved" in i.message for i in issues)


def test_flags_empty_answer():
    bundle = _bundle([_item()])
    result = _result(bundle, answer="   ", cited_evidence_indices=(1,))

    issues = AnswerValidator().validate(result, bundle)

    assert any("empty" in i.message.lower() for i in issues)


def test_warns_on_sufficient_but_uncited_answer():
    bundle = _bundle([_item()])
    result = _result(bundle, evidence_sufficient=True, cited_evidence_indices=())

    issues = AnswerValidator().validate(result, bundle)

    assert any(i.severity == ValidationSeverity.WARNING for i in issues)


def test_no_warning_when_evidence_insufficient_and_uncited():
    bundle = _bundle([_item()])
    result = _result(bundle, evidence_sufficient=False, cited_evidence_indices=())

    issues = AnswerValidator().validate(result, bundle)

    assert issues == []
