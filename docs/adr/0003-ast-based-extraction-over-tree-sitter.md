# 0003. AST-Based Static Extraction over Tree-sitter

## Status

Accepted

## Context

Repository Intelligence needs to extract symbols, imports, calls, and class hierarchy from source. Tree-sitter was
named in the original tech stack and is the more future-proof long-term choice for multi-language support (a
uniform query API, error-tolerant parsing) - but for Python specifically, the standard library's `ast` module
already does this well, with zero new dependencies, and the project's pre-existing text-chunking pipeline
(`chunking/python_chunker.py`) already used it successfully.

## Decision

Use `ast` for both text chunking (pre-existing) and structural extraction (`intelligence/python_extractor.py`),
rather than introducing Tree-sitter as a second parser for Python alone. This was an explicit fork, discussed and
decided against tree-sitter-for-Python specifically - see
[0002](0002-python-first-before-multi-language-expansion.md) for the broader multi-language framing this sits
inside.

## Consequences

One parser, one dependency, less code - at the cost of no current path to a second language without introducing a
new parsing layer when that day comes. The extracted `RepoStructure` model doesn't assume `ast` internals (it's
just `Symbol`s and `*Edge`s), so a future Tree-sitter-based extractor for another language could produce the same
`RepoStructure` shape and plug in without changing `SymbolTable`, `graph_builder.py`, `RepoIntelligenceStore`, or
anything built on top of them (see [0005](0005-knowledgebase-as-the-sole-access-boundary.md)).
