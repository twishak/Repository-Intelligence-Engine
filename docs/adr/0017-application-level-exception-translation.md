# 0017. Application-Level Exception Translation at the Service Boundary

## Status

Accepted

## Context

Lower layers already raise meaningful, typed exceptions - `RepoNotIngestedError`, `IncompatibleSchemaError` from
the Knowledge Layer. The CLI and API both need to react to "this repo doesn't exist" and "this repo needs
re-ingesting" with different user-facing behavior (an HTTP status code in one case, an exit code and message in
the other) - but neither should need to know that these specific exception types come from
`codebase_agent.knowledge` specifically, any more than they should know `KnowledgeBase` is backed by JSON and
Chroma ([0005](0005-knowledgebase-as-the-sole-access-boundary.md)).

## Decision

A small `ApplicationError` hierarchy (`RepositoryNotFoundError`, `RepositoryIncompatibleError`,
`IngestionFailedError`) is what the CLI and API actually catch. Translation happens once, at the service boundary -
a shared `get_knowledge_base()` helper (`application/services/_kb_lookup.py`) used by the three services that look
up a `KnowledgeBase`, catching `RepoNotIngestedError` / `IncompatibleSchemaError` and re-raising the corresponding
`ApplicationError`. No generic catch-all for unexpected failures (a Groq outage, a bug) was added - those
subsystems already degrade gracefully for their own expected failure modes
([0004](0004-best-effort-symbol-resolution-keep-unresolved-edges.md), the reasoning engine's fallback, the analysis
runner's per-analyzer warnings); anything that still raises past that is genuinely unexpected and should propagate
honestly rather than be smoothed into a misleadingly generic wrapper.

## Consequences

FastAPI registers one exception handler per `ApplicationError` subtype, mapped to the right HTTP status
(404/409/422), plus a base-class handler as a safety net for any future subtype that doesn't get its own explicit
mapping. The CLI catches `ApplicationError` once, in one place, rather than per-command. Adding a fifth service
later that needs its own new failure mode means adding one new `ApplicationError` subtype, not auditing every
existing catch site.
