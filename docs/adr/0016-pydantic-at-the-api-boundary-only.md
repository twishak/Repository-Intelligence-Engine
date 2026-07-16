# 0016. Pydantic at the API Boundary Only, Domain Dataclasses Through the Service Layer

## Status

Accepted

## Context

[0011](0011-dataclasses-over-pydantic-for-domain-models.md) deferred introducing Pydantic to "the future Interfaces
feature... where request/response validation at an actual network boundary is the point." The Presentation Layer
is that feature. The question this time: should Application Services themselves return Pydantic models (so FastAPI
can serialize them directly), or should Pydantic conversion happen even further out, only inside route handlers?

## Decision

Application Services return the same domain dataclasses the underlying subsystems already produce - `RepoMetadata`,
`ReasoningResult`, `RepositoryReport` - unchanged. Pydantic models exist only in `api/schemas.py`, each with a
`from_domain(...)` classmethod that route handlers call to convert. The CLI never touches Pydantic at all - it
renders the same dataclasses directly with Rich.

## Consequences

A service's return type means the same thing whether it's called from the CLI, the API, or a test - there's
exactly one "answer to a question" shape (`ReasoningResult`), not a service-layer version and an API-layer version
that must be kept in sync. The API layer carries a real but small translation cost (one `from_domain` method per
response schema) in exchange for keeping Pydantic's actual value - request validation and OpenAPI generation -
scoped to where it's needed rather than letting HTTP concerns leak into the service layer, consistent with
[0007](0007-normalized-structured-outputs-at-layer-boundaries.md)'s "normalize at the boundary, not before" theme.
