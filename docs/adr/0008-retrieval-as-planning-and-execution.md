# 0008. Retrieval as Planning + Execution over a Monolithic Retriever

## Status

Accepted

## Context

The original retrieval implementation (`retrieval/retriever.py`'s `CodeRetriever`, still present but superseded)
was a single class with three hardcoded methods, chosen by one LLM routing call. Extending this to cover
five-plus strategies (symbol lookup, semantic search, call graph, import graph, hierarchy) with any hope of
independent testability meant either growing one class indefinitely or splitting responsibilities.

## Decision

Split into three concerns:

1. `RetrievalPlanner` classifies a question into a `RetrievalPlan` - one LLM call, no `KnowledgeBase` access (it
   reasons about question shape only).
2. `RetrievalExecutor` dispatches each planned step to one of five specialized, independently-testable retrievers
   (`SymbolRetriever`, `SemanticRetriever`, `CallGraphRetriever`, `ImportRetriever`, `HierarchyRetriever`), each
   behind a `SpecializedRetriever` Protocol.
3. Aggregation into an `EvidenceBundle` ([0007](0007-normalized-structured-outputs-at-layer-boundaries.md)).

Compound intents (e.g. impact analysis: "what would break if I changed X") become multiple planned steps
(`symbol_lookup` to resolve X, then `call_graph` with direction=`callers`), not a sixth hardcoded strategy.

## Consequences

Adding a sixth retrieval strategy means adding one retriever class and one registry entry, not touching the
executor. Steps execute independently, with no data flow between them - a step needing a resolved symbol re-resolves
it itself via a shared helper, rather than the executor threading state between steps. This is simpler, but means
the same short-name resolution logic runs more than once per plan when several steps reference the same target. A
failing step is recorded as a warning and skipped, not fatal to the whole plan - the same graceful-degradation
philosophy carried into [0009](0009-deterministic-single-pass-orchestration.md) and
[0014](0014-independent-composable-analyzers.md).
