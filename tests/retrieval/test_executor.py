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


def test_falls_back_to_semantic_search_when_structured_retrieval_finds_nothing():
    # Regression test: a plan built entirely from structured strategies
    # (symbol_lookup, call_graph, import_graph, hierarchy) can return zero
    # evidence when the planner's target doesn't resolve to a real symbol -
    # e.g. a hallucinated or malformed identifier. Falling back to
    # semantic_search over the raw question recovers evidence a human would
    # still expect to see, instead of silently reporting "no evidence".
    structured = Mock()
    structured.retrieve.return_value = []
    semantic = Mock()
    semantic.retrieve.return_value = [_item()]
    executor = RetrievalExecutor(
        retrievers={
            RetrievalStrategy.SYMBOL_LOOKUP: structured,
            RetrievalStrategy.SEMANTIC_SEARCH: semantic,
        }
    )
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="x"),)
    )

    bundle = executor.execute(Mock(), "what does the x decorator do", plan)

    assert len(bundle) == 1
    semantic.retrieve.assert_called_once()
    fallback_step = semantic.retrieve.call_args.args[1]
    assert fallback_step.strategy == RetrievalStrategy.SEMANTIC_SEARCH
    assert fallback_step.query == "what does the x decorator do"
    assert RetrievalStrategy.SEMANTIC_SEARCH in bundle.retrievers_used


def test_fallback_logs_why_it_triggered(caplog):
    structured = Mock()
    structured.retrieve.return_value = []
    semantic = Mock()
    semantic.retrieve.return_value = []
    executor = RetrievalExecutor(
        retrievers={
            RetrievalStrategy.SYMBOL_LOOKUP: structured,
            RetrievalStrategy.SEMANTIC_SEARCH: semantic,
        }
    )
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="x"),)
    )

    with caplog.at_level("WARNING"):
        executor.execute(Mock(), "what does the x decorator do", plan)

    assert any(
        "falling back to semantic_search" in record.message for record in caplog.records
    )


def test_does_not_fall_back_when_structured_retrieval_finds_evidence():
    structured = Mock()
    structured.retrieve.return_value = [_item()]
    semantic = Mock()
    executor = RetrievalExecutor(
        retrievers={
            RetrievalStrategy.SYMBOL_LOOKUP: structured,
            RetrievalStrategy.SEMANTIC_SEARCH: semantic,
        }
    )
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="x"),)
    )

    executor.execute(Mock(), "q", plan)

    semantic.retrieve.assert_not_called()


def test_does_not_fall_back_when_plan_already_includes_semantic_search():
    semantic = Mock()
    semantic.retrieve.return_value = []
    executor = RetrievalExecutor(
        retrievers={RetrievalStrategy.SEMANTIC_SEARCH: semantic}
    )
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query="q"),)
    )

    executor.execute(Mock(), "q", plan)

    semantic.retrieve.assert_called_once()


def test_fallback_handles_missing_semantic_search_retriever_gracefully():
    structured = Mock()
    structured.retrieve.return_value = []
    executor = RetrievalExecutor(
        retrievers={RetrievalStrategy.SYMBOL_LOOKUP: structured}
    )
    plan = RetrievalPlan(
        steps=(RetrievalStep(strategy=RetrievalStrategy.SYMBOL_LOOKUP, target="x"),)
    )

    bundle = executor.execute(Mock(), "q", plan)

    assert bundle.is_empty()
    assert len(bundle.warnings) == 1


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
