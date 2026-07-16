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


def _item(
    source: EvidenceSource = EvidenceSource.SYMBOL, confidence: float | None = 0.5
) -> EvidenceItem:
    return EvidenceItem(
        source=source,
        qualified_name="pkg.a.foo",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        content="...",
        explanation="...",
        confidence=confidence,
    )


def _bundle(items: list[EvidenceItem]) -> EvidenceBundle:
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH),)
    )
    return EvidenceBundle(
        question="q",
        plan=plan,
        items=tuple(items),
        retrievers_used=(),
        warnings=(),
        execution_time_seconds=0.01,
    )


def test_by_source():
    a = _item(source=EvidenceSource.SYMBOL)
    b = _item(source=EvidenceSource.SEMANTIC)
    bundle = _bundle([a, b])

    assert bundle.by_source(EvidenceSource.SYMBOL) == [a]


def test_sorted_by_confidence_treats_none_as_lowest():
    low = _item(confidence=0.2)
    high = _item(confidence=0.9)
    none_conf = _item(confidence=None)
    bundle = _bundle([low, high, none_conf])

    assert bundle.sorted_by_confidence() == [high, low, none_conf]


def test_is_empty():
    assert _bundle([]).is_empty() is True
    assert _bundle([_item()]).is_empty() is False


def test_len_and_iter():
    items = [_item(), _item()]
    bundle = _bundle(items)

    assert len(bundle) == 2
    assert list(bundle) == items
