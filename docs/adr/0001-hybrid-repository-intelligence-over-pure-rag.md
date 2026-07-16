# 0001. Hybrid Repository Intelligence over Pure RAG

## Status

Accepted

## Context

Many "codebase Q&A" tools are built as a thin RAG wrapper: chunk the repo, embed it, vector-search, stuff the top-k
results into an LLM prompt. This works reasonably well for open-ended/conceptual questions ("where is X handled"),
but breaks down for exactly the questions that make a tool feel like it *understands* code rather than just search
over it: "what would break if I changed this function," "which files depend on this module," "is there a circular
dependency," "find dead code." These require structural facts - call graphs, import graphs, class hierarchies - that
don't exist in embedding space at all. No amount of better retrieval over vector search recovers a fact like "this
function has zero callers" if that fact was never computed in the first place.

## Decision

Combine four complementary knowledge sources instead of relying on one:

1. **Static analysis** (Repository Intelligence, see [0003](0003-ast-based-extraction-over-tree-sitter.md) and
   [0004](0004-best-effort-symbol-resolution-keep-unresolved-edges.md)) producing a symbol table and
   call/import/inheritance graphs.
2. **Semantic retrieval** (vector search) for open-ended/conceptual questions.
3. **A unified access layer** ([`KnowledgeBase`](0005-knowledgebase-as-the-sole-access-boundary.md)) so consumers
   don't need to care which source answered a given lookup.
4. **Evidence-grounded reasoning** ([0007](0007-normalized-structured-outputs-at-layer-boundaries.md),
   [0009](0009-deterministic-single-pass-orchestration.md), [0010](0010-index-based-citation-resolution.md)) that
   cites its sources rather than free-associating.

RAG is one retrieval strategy among five ([0008](0008-retrieval-as-planning-and-execution.md)), not the whole
system.

## Consequences

Significantly more implementation surface than a RAG-only chatbot - five subsystems instead of one embed-and-search
loop, and static analysis over a dynamic language like Python is inherently incomplete
([0004](0004-best-effort-symbol-resolution-keep-unresolved-edges.md)). In exchange, the system can answer structural
questions a pure-RAG system fundamentally cannot, and every answer can be traced back to a specific file, line, or
graph edge instead of "the LLM said so." This is the foundational bet the whole project makes; nearly every other
ADR in this log is a consequence of this one.
