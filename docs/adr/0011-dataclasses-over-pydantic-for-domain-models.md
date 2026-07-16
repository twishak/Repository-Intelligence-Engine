# 0011. Dataclasses for Internal Domain Models, Pydantic Reserved for the API Boundary

## Status

Accepted

## Context

The project's tech stack names Pydantic, and by the time `ReasoningResult` was designed there was a real fork:
every domain model up to that point (`SourceFile`, `CodeChunk`, `Symbol`, `CallEdge`, `RetrievedChunk`,
`EvidenceItem`, `EvidenceBundle`, ...) is a frozen dataclass, while `ReasoningResult` is arguably the first genuine
"public output" object - the kind of thing that would eventually get serialized across a REST API, where
Pydantic's validation and JSON-schema generation are most valuable.

## Decision

Keep `ReasoningResult` (and its siblings `Citation`, `ValidationIssue`, and later `Finding`) as frozen dataclasses,
for consistency with every other model in the codebase, rather than introducing Pydantic for one class. Pydantic is
deliberately reserved for the future Interfaces feature (the REST API mentioned in
[0001](0001-hybrid-repository-intelligence-over-pure-rag.md)), where request/response validation at an actual
network boundary is the point, rather than for the internal domain layer.

## Consequences

One modeling convention throughout the codebase - no "why is this one different" question for future maintainers -
at the cost of not yet getting Pydantic's free JSON-schema generation or field validation anywhere. When the REST
API is built, it will likely wrap these dataclasses in Pydantic response models rather than replacing them, meaning
two representations of similar data at that boundary - judged acceptable since that's exactly where Pydantic's
value (a real external contract) actually applies.
