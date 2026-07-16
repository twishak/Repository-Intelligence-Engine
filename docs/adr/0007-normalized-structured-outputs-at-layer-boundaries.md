# 0007. Normalized Structured Outputs at Layer Boundaries

## Status

Accepted

## Context

Each of Retrieval, Reasoning, and Insights aggregates results from several independent producers - five retrievers,
one LLM call, five analyzers, respectively - into one collection consumed by the next layer up. Each producer
naturally has its own internal data shape (`Symbol`, `CallEdge`, `ImportEdge`, `InheritsEdge`, `RetrievedChunk` for
Retrieval's sources; raw LLM tool-call output for Reasoning). Two options exist at each such boundary: expose those
internal shapes directly to the layer above (via a union type or a "raw" field), or normalize every producer's
output into one common shape before it crosses the boundary.

## Decision

Normalize, consistently, at every layer boundary:

- `EvidenceItem` (Retrieval, [0008](0008-retrieval-as-planning-and-execution.md)) has one shape regardless of which
  of the five retrievers produced it - no `raw: Symbol | CallEdge | ...` field, deliberately removed from an early
  draft.
- `Citation` (Reasoning, [0010](0010-index-based-citation-resolution.md)) is a small normalized location reference,
  not the underlying evidence item.
- `Finding` (Insights, [0014](0014-independent-composable-analyzers.md)) has one shape regardless of which of the
  five analyzers produced it, with an analyzer-specific `details` dict for the few numbers that don't merit a
  first-class field.

In each case the normalized shape - not the producer's internal type - is what the next layer, a future API
response, or a Markdown/JSON exporter actually consumes.

## Consequences

Consumers get one rendering/serialization path instead of N type-specific ones, and internal producer types
(`Symbol`, `CallEdge`, raw LLM JSON) never leak into a layer's public output, preserving the substitutability
[0005](0005-knowledgebase-as-the-sole-access-boundary.md) established for `KnowledgeBase` itself. The cost is a
small amount of information loss at each boundary (an unusual field on a specific edge type that didn't make it
into the normalized shape is genuinely unavailable downstream) and a bit of repeated "extract common fields" glue
code, once per producer.
