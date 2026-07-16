# Architecture Decision Records

This log records the significant, hard-to-reverse architectural decisions behind this project, in
[Nygard format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (Title, Status, Context,
Decision, Consequences). Numbering follows narrative order, not strictly chronological order - the two foundational
decisions come first, followed by decisions in roughly the order the corresponding subsystem was built. ADRs
cross-reference each other where one decision is a consequence, instance, or extension of another, so this reads as
a connected narrative rather than a pile of isolated documents.

| # | Title | Status |
|---|---|---|
| [0001](0001-hybrid-repository-intelligence-over-pure-rag.md) | Hybrid Repository Intelligence over Pure RAG | Accepted |
| [0002](0002-python-first-before-multi-language-expansion.md) | Python-First Before Multi-Language Expansion | Accepted |
| [0003](0003-ast-based-extraction-over-tree-sitter.md) | AST-Based Static Extraction over Tree-sitter | Accepted |
| [0004](0004-best-effort-symbol-resolution-keep-unresolved-edges.md) | Best-Effort Symbol Resolution: Keep Unresolved Edges, Never Drop Them | Accepted |
| [0005](0005-knowledgebase-as-the-sole-access-boundary.md) | KnowledgeBase as the Sole Access Boundary for Repository Knowledge | Accepted |
| [0006](0006-self-contained-persisted-artifacts.md) | Self-Contained Persisted Artifacts, Independent of the Original Checkout | Accepted |
| [0007](0007-normalized-structured-outputs-at-layer-boundaries.md) | Normalized Structured Outputs at Layer Boundaries | Accepted |
| [0008](0008-retrieval-as-planning-and-execution.md) | Retrieval as Planning + Execution over a Monolithic Retriever | Accepted |
| [0009](0009-deterministic-single-pass-orchestration.md) | Deterministic Single-Pass Orchestration over Agentic Tool-Calling Loops | Accepted |
| [0010](0010-index-based-citation-resolution.md) | Index-Based Citation Resolution for Trustworthy Grounding | Accepted |
| [0011](0011-dataclasses-over-pydantic-for-domain-models.md) | Dataclasses for Internal Domain Models, Pydantic Reserved for the API Boundary | Accepted |
| [0012](0012-deterministic-non-llm-answer-validation.md) | Deterministic, Non-LLM Answer Validation over Self-Correcting Re-Prompting | Accepted |
| [0013](0013-external-versioned-prompt-templates.md) | External, Versioned Prompt Templates | Accepted |
| [0014](0014-independent-composable-analyzers.md) | Independent, Composable Analyzers over Monolithic Repository Scanning | Accepted |
| [0015](0015-application-service-layer-as-the-sole-boundary.md) | Application Service Layer as the Sole Boundary for CLI and API | Accepted |
| [0016](0016-pydantic-at-the-api-boundary-only.md) | Pydantic at the API Boundary Only, Domain Dataclasses Through the Service Layer | Accepted |
| [0017](0017-application-level-exception-translation.md) | Application-Level Exception Translation at the Service Boundary | Accepted |
| [0018](0018-shared-singletons-via-app-state.md) | Shared Long-Lived Singletons via app.state, Services Rebuilt per Request | Accepted |
| [0019](0019-lightweight-request-correlation.md) | Lightweight Request Correlation via Context-Local Request IDs, Not Distributed Tracing | Accepted |

## Adding a new ADR

1. Copy the highest-numbered file as a starting point for structure.
2. Number sequentially, `NNNN-kebab-case-title.md`.
3. Use `Proposed` while a decision is still being designed/discussed, `Accepted` once implemented, `Deprecated` or
   `Superseded by NNNN` if a later decision replaces it - never edit an old ADR's Decision/Consequences to match a
   new choice; write a new ADR and mark the old one superseded.
4. Cross-reference related ADRs by number and link, both ways where practical.
5. Add a row to the table above.
