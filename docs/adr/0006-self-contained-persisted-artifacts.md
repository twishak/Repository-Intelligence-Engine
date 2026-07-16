# 0006. Self-Contained Persisted Artifacts, Independent of the Original Checkout

## Status

Accepted

## Context

`KnowledgeBase.get_source(qualified_name)` could either read from the on-disk repo checkout
(`data/repos/<repo>/...`) at query time, or from data captured once at ingestion time. Reading from disk is simpler
and avoids storing text twice (Chroma already holds chunk text) - but it means the Knowledge Layer's artifacts are
not actually self-contained: querying a repo requires the original checkout to still exist, unmoved, on the same
machine.

## Decision

Persist exact source text at ingestion time instead: `SymbolSourceStore` slices each symbol's precise
`start_line:end_line` text into `sources.json`, keyed by qualified name. Insights extends the same principle to
whole-file text (`FileSourceStore`, needed for TODO/FIXME scanning, which requires text outside any symbol's
bounds - see [0014](0014-independent-composable-analyzers.md)) rather than falling back to disk reads for that one
analyzer.

## Consequences

Some real duplication - the same source text now lives in Chroma (chunk-granular), `sources.json`
(symbol-granular), and `files.json` (file-granular) - accepted because it's cheap at this project's scale and each
serves a different access pattern (similarity search vs. exact structured lookup vs. full-text scan). In exchange,
a `KnowledgeBase` built from persisted artifacts alone can answer `get_source` / `get_file_source` even if the
original checkout is deleted, moved, or was only ever a temporary clone - relevant for any future hosted/API
scenario ([0001](0001-hybrid-repository-intelligence-over-pure-rag.md)) that shouldn't need to keep every ingested
repo checked out forever.
