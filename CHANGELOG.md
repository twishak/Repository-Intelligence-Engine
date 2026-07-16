# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

Everything below predates the first tagged release - it will become the `1.0.0` entry once released.

### Added

- **Repository Intelligence** (`codebase_agent.intelligence`): `ast`-based static analysis producing a repo-wide
  symbol table and call/import/class-hierarchy graphs, with best-effort symbol resolution that keeps unresolved
  edges instead of dropping them.
- **Knowledge Layer** (`codebase_agent.knowledge`): a single `KnowledgeBase` access boundary composing Repository
  Intelligence, persisted source snippets, the vector store, and versioned per-repo metadata.
- **Reasoning Retrieval Engine** (`codebase_agent.retrieval`): a planner/executor pipeline (symbol, semantic, call
  graph, import graph, and hierarchy retrievers) that gathers grounded evidence without generating prose.
- **Reasoning Engine** (`codebase_agent.reasoning`): a deterministic, single-pass LangGraph pipeline turning
  retrieved evidence into a citation-backed, confidence-scored answer, with a deterministic non-LLM validation pass.
- **Repository Insights** (`codebase_agent.insights`): five independent, deterministic, LLM-free analyzers (dead
  code, circular dependencies, complexity, TODO/FIXME, architecture) producing a unified `RepositoryReport`.
- **Presentation Layer**: a Typer CLI (`codebase-agent` / `scripts/cli.py`) and a FastAPI REST API
  (`scripts/serve_api.py`), both built exclusively on an Application Service layer so neither talks to the lower
  layers directly.
- 19 [Architecture Decision Records](docs/adr/README.md) documenting the reasoning behind the design, plus
  [`docs/architecture.md`](docs/architecture.md) explaining how the layers fit together.
- A real, runnable example repo at [`examples/demo`](examples/demo) for the README Quick Start.
- Apache-2.0 [LICENSE](LICENSE), GitHub Actions CI, and a locked dependency set (`requirements.lock`) for
  reproducible installs.
- [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Fixed

- Import resolution returned 0% resolved imports for repos using the PyPA "src layout" convention
  (`src/<package>/...`) - module-path resolution now correctly strips the `src/` prefix before matching.

### Changed

- Project display name to "Repository Intelligence Engine" (provisional - the public repo name isn't finalized).
  The importable Python package (`codebase_agent`) and the `codebase-agent` CLI command are unchanged.
