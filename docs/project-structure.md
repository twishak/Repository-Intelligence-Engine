# Project Structure

```text
src/codebase_agent/
  intelligence/   AST-based static analysis: symbol table, call/import/inheritance graphs
  ingestion/      Discovers and loads source files from a repo checkout
  chunking/       Splits source files into embeddable chunks
  embeddings/     Embeds chunks with a local sentence-transformers model
  storage/        Persists chunk vectors in ChromaDB
  knowledge/      KnowledgeBase - the single access boundary everything above depends on
  retrieval/      Plans and executes evidence retrieval for a question
  reasoning/      Turns retrieved evidence into a citation-backed, confidence-scored answer
  insights/       Five deterministic, LLM-free repository analyzers
  application/    Application Services - the only thing the CLI/API call into
  api/            REST API (FastAPI): routes, Pydantic schemas, dependency wiring
  cli/            CLI (Typer)
  llm/            Legacy pipeline: the original Groq client wrapper
  graph/          Legacy pipeline: the original LangGraph router/retrieve/answer flow
  interface/      Legacy pipeline: the original Rich-rendered CLI
  config.py       pydantic-settings, .env-driven configuration

docs/
  architecture.md         How the layers fit together and why
  question-answering.md   The ask/retrieval/reasoning pipeline in depth
  repository-insights.md  The five analyzers in depth
  cli-and-api.md          Full CLI command and REST route reference
  project-structure.md    This file
  adr/                    19 Architecture Decision Records, one per non-obvious design choice

examples/demo/    A tiny real 3-file repo used throughout the README and docs - ingest it with zero setup
scripts/
  cli.py            Entry point for the `codebase-agent` command
  serve_api.py      Entry point for the REST API (uvicorn)
  ingest_repo.py     Original end-to-end ingest pipeline; still what every ingestion path calls
  analyze_repo.py    Standalone entry point for running Repository Insights
  ask.py, ask_v2.py  Legacy pipeline entry points, kept for reference - see architecture.md's Legacy pipeline section

tests/            Mirrors the src/codebase_agent package layout, one test module per source module
data/             Gitignored local artifacts: ingested repo checkouts, graph/knowledge JSON, the Chroma vector store
```

## Legacy pipeline

`codebase_agent.llm`, `codebase_agent.graph`, `codebase_agent.interface`, and the legacy `CodeRetriever`
(`codebase_agent.retrieval.retriever`) predate the layered design described in `architecture.md`. They're
superseded in normal usage by the Reasoning Retrieval Engine and Reasoning Engine, but kept in place and untouched
rather than deleted - see [`architecture.md`](architecture.md#legacy-pipeline) for why, and
[CONTRIBUTING.md](../CONTRIBUTING.md) for the project rule against modifying it as a side effect of unrelated work.

## See also

- [`architecture.md`](architecture.md) - how these packages depend on each other, and why
- [ADR index](adr/README.md) - the reasoning behind individual structural decisions
