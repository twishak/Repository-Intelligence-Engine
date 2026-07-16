# 0014. Independent, Composable Analyzers over Monolithic Repository Scanning

## Status

Accepted

## Context

"Repository Insights" (dead code, circular dependencies, complexity, TODOs, architecture) could be implemented as
one script or class that walks the repository once and produces several kinds of output, or as independent units
each responsible for one analysis. A monolithic scanner is simpler to write once, but couples unrelated concerns
(a bug in complexity scoring could break TODO extraction) and is harder to test in isolation or extend with a sixth
analysis later.

## Decision

Each analysis is an independent `Analyzer` (`name: str`, `analyze(kb: KnowledgeBase) -> list[Finding]`), depending
only on `KnowledgeBase` ([0005](0005-knowledgebase-as-the-sole-access-boundary.md)) - never on Chroma, JSON, or
NetworkX directly. An `AnalysisRunner` (mirroring `RetrievalExecutor`,
[0008](0008-retrieval-as-planning-and-execution.md)) dispatches each registered analyzer and aggregates results
into a `RepositoryReport`; one analyzer failing is recorded as a warning and doesn't blank the rest of the report -
the same graceful-degradation philosophy as [0008](0008-retrieval-as-planning-and-execution.md)'s executor.
Findings use one normalized `Finding` shape across all five analyzers
([0007](0007-normalized-structured-outputs-at-layer-boundaries.md)), not five analyzer-specific types.

## Consequences

Adding a sixth analysis (e.g. duplicate-code detection) means adding one class and one registry entry, with its own
independent test suite, and never risks breaking the other five. Because analyzers only see `KnowledgeBase`,
whole-repo analyses (circular dependencies, dead code, TODOs across every file) require the Protocol to expose
repo-wide enumeration (`all_symbols`, `all_import_edges`, `all_call_edges`, `all_inherits_edges`,
`get_file_source`) - a deliberate, explicit extension of [0005](0005-knowledgebase-as-the-sole-access-boundary.md)'s
boundary, and of [0006](0006-self-contained-persisted-artifacts.md)'s self-containment principle, not a workaround
of either. Dead-code findings inherit [0004](0004-best-effort-symbol-resolution-keep-unresolved-edges.md)'s
honesty: they're reported as `WARNING`-severity candidates with an explicit "may be a false positive" caveat, never
asserted as certain, because they're built on the same best-effort call graph.
