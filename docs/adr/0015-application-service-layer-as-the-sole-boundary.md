# 0015. Application Service Layer as the Sole Boundary for CLI and API

## Status

Accepted

## Context

By the time a CLI and a REST API both need repository capabilities, both need to ingest, ask questions, run
analysis, and look up repos. Letting CLI commands and FastAPI routes call `KnowledgeBaseRegistry`,
`RetrievalPlanner`/`RetrievalExecutor`, `ReasoningEngine`, and `AnalysisRunner` directly would mean two
presentation surfaces independently re-implementing the same orchestration (the exact ingestion sequence, the
exact reasoning pipeline wiring), with any change to that orchestration needing to be made in two places kept in
sync by convention rather than by the type system. This is the same problem
[0005](0005-knowledgebase-as-the-sole-access-boundary.md) solved one layer down.

## Decision

Four Application Services - `IngestionService`, `ReasoningService`, `InsightsService`, `RepositoryService` - are
the only thing the CLI and FastAPI depend on. Neither imports `intelligence`, `knowledge`, `retrieval`,
`reasoning`, or `insights` directly. Each service contains no new business logic - it's the same orchestration the
existing scripts (`scripts/ingest_repo.py`, `scripts/ask_v2.py`, `scripts/analyze_repo.py`) already performed,
moved into a reusable, constructor-injectable class so two presentation surfaces can share one implementation
instead of maintaining two copies.

## Consequences

A third presentation surface (a future web UI, a batch job) gets the same guarantees for free - it depends on the
same four services, not on relearning how to wire five subsystems together correctly. The cost: an extra
indirection layer for what were, in the legacy scripts, single functions - `IngestionService.ingest_repository` is
a class wrapping what `ingest_repo.py`'s `main()` did inline. Ingestion also stays synchronous through this layer
(a blocking call from HTTP's perspective) - building asynchronous job handling (a background task plus status
polling) would be a new capability, not an exposure of an existing one, and was deliberately left out of scope.
