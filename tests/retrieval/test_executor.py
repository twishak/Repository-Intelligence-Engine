from unittest.mock import Mock

from codebase_agent.retrieval.evidence import EvidenceItem, EvidenceSource
from codebase_agent.retrieval.executor import RetrievalExecutor
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalStep,
    RetrievalStrategy,
)


def _item(confidence: float | None = None) -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.SYMBOL,
        qualified_name="pkg.a.foo",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        content="...",
        explanation="...",
        confidence=confidence,
    )


def test_dispatches_to_matching_retriever():
    retriever = Mock()
    retriever.retrieve.return_value = [_item()]
    executor = RetrievalExecutor(
        retrievers={RetrievalStrategy.SYMBOL_LOOKUP: retriever}
    )
    step = RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="foo")
    plan = RetrievalPlan(steps=(step,))
    kb = Mock()

    bundle = executor.execute(kb, "question", plan)

    retriever.retrieve.assert_called_once_with(kb, step)
    assert len(bundle) == 1
    assert bundle.question == "question"
    assert bundle.plan is plan
    assert bundle.retrievers_used == (RetrievalStrategy.SYMBOL_LOOKUP,)
    assert bundle.warnings == ()
    assert bundle.execution_time_seconds >= 0


def test_records_warning_for_unregistered_strategy():
    executor = RetrievalExecutor(retrievers={})
    step = RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="q")
    plan = RetrievalPlan(steps=(step,))

    bundle = executor.execute(Mock(), "q", plan)

    assert bundle.is_empty()
    assert len(bundle.warnings) == 1
    assert bundle.warnings[0].step == step


def test_continues_after_a_failing_step():
    failing = Mock()
    failing.retrieve.side_effect = RuntimeError("boom")
    working = Mock()
    working.retrieve.return_value = [_item()]
    executor = RetrievalExecutor(
        retrievers={
            RetrievalStrategy.SYMBOL_LOOKUP: failing,
            RetrievalStrategy.SEMANTIC_SEARCH: working,
        }
    )
    plan = RetrievalPlan(
        steps=(
            RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="foo"),
            RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="q"),
        )
    )

    bundle = executor.execute(Mock(), "q", plan)

    assert len(bundle) == 1
    assert len(bundle.warnings) == 1
    assert "boom" in bundle.warnings[0].message


def test_max_results_truncates_to_highest_confidence():
    retriever = Mock()
    retriever.retrieve.return_value = [
        _item(confidence=0.1),
        _item(confidence=0.9),
        _item(confidence=0.5),
    ]
    executor = RetrievalExecutor(
        retrievers={RetrievalStrategy.SEMANTIC_SEARCH: retriever}
    )
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="q"),),
        max_results=2,
    )

    bundle = executor.execute(Mock(), "q", plan)

    assert len(bundle) == 2
    assert [i.confidence for i in bundle.items] == [0.9, 0.5]


def test_no_max_results_keeps_all_items():
    retriever = Mock()
    retriever.retrieve.return_value = [_item(), _item()]
    executor = RetrievalExecutor(
        retrievers={RetrievalStrategy.SEMANTIC_SEARCH: retriever}
    )
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="q"),)
    )

    bundle = executor.execute(Mock(), "q", plan)

    assert len(bundle) == 2


def test_retrievers_used_dedupes_and_preserves_order():
    retriever = Mock()
    retriever.retrieve.return_value = []
    executor = RetrievalExecutor(
        retrievers={RetrievalStrategy.SEMANTIC_SEARCH: retriever}
    )
    plan = RetrievalPlan(
        steps=(
            RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="a"),
            RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="b"),
        )
    )

    bundle = executor.execute(Mock(), "q", plan)

    assert bundle.retrievers_used == (RetrievalStrategy.SEMANTIC_SEARCH,)
