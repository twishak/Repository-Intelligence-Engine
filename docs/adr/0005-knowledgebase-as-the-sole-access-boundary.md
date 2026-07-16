# 0005. KnowledgeBase as the Sole Access Boundary for Repository Knowledge

## Status

Accepted

## Context

By the time Retrieval, Reasoning, and Insights all need repository data, there are several physically different
storage mechanisms in play - Chroma (vectors), JSON (symbols/edges/metadata), and eventually more. Letting every
subsystem query these directly would mean five-plus places knowing about Chroma collection naming, JSON file
layout, and NetworkX node conventions, and any storage change would ripple through all of them. (This is the same
"not just RAG" bet from [0001](0001-hybrid-repository-intelligence-over-pure-rag.md), applied to the access layer
rather than just the retrieval strategy.)

## Decision

`KnowledgeBase` (a `Protocol`) is the only interface any subsystem above it depends on - Retrieval, Reasoning,
Insights, the CLI, and the future REST API all talk to `KnowledgeBase`, never to `CodeVectorStore`,
`RepoIntelligenceStore`, or raw JSON/NetworkX. `DefaultKnowledgeBase` is the concrete implementation;
`KnowledgeBaseFactory` builds instances (construction) and `KnowledgeBaseRegistry` caches them per repo (lifecycle)
- kept as separate classes so neither does both jobs. The interface itself is deliberately atomic (symbol/caller/
callee/import/inheritance lookups, semantic search, metadata) - no ranking, no multi-hop composition; that's
Retrieval's job ([0008](0008-retrieval-as-planning-and-execution.md)), built by composing these primitives.

## Consequences

Any future storage swap (SQLite instead of JSON, a graph database instead of NetworkX) only touches
`DefaultKnowledgeBase` and its stores - every consumer is unaffected by construction. The atomicity constraint means
new whole-repo query needs (like Insights' analyzers, [0014](0014-independent-composable-analyzers.md)) require
deliberately extending the Protocol rather than reaching around it - a small recurring tax, paid more than once so
far, judged worth it to keep the boundary real rather than aspirational.
