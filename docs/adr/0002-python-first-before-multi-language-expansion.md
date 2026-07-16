# 0002. Python-First Before Multi-Language Expansion

## Status

Accepted

## Context

The original tech stack named Tree-sitter, implying multi-language parsing from the start. Building a genuinely
good multi-language abstraction - a parser interface, per-language extractors, a language-agnostic symbol/graph
model - before validating that abstraction against a single real, well-understood language risks over-engineering
the abstraction around guesses rather than field-tested requirements, and risks a shallower, buggier single-language
implementation while attention is split across N languages.

## Decision

Build Repository Intelligence, the Knowledge Layer, Retrieval, and Reasoning against Python only, using Python's
own `ast` module (see [0003](0003-ast-based-extraction-over-tree-sitter.md)) rather than Tree-sitter, until the
Python-only implementation is deep and correct. Multi-language support is deferred, not abandoned:
`intelligence/python_extractor.py`'s output shape (`Symbol`, `ImportEdge`, `CallEdge`, `InheritsEdge`) was kept
storage- and language-agnostic specifically so a second language's extractor could plug into the same
`RepoStructure` / `KnowledgeBase` pipeline later without redesigning those layers.

## Consequences

The project currently only understands Python repositories. Adding a second language later means introducing
Tree-sitter (or another parser) for genuine multi-language support, which was explicitly deferred rather than
solved now (see [0003](0003-ast-based-extraction-over-tree-sitter.md), "what we didn't do"). The upside actually
realized: four subsystems' worth of architectural depth - graph resolution heuristics
([0004](0004-best-effort-symbol-resolution-keep-unresolved-edges.md)), evidence normalization
([0007](0007-normalized-structured-outputs-at-layer-boundaries.md)), citation grounding
([0010](0010-index-based-citation-resolution.md)), deterministic reasoning
([0009](0009-deterministic-single-pass-orchestration.md)) - that would have been much harder to get right while
simultaneously chasing N languages.
