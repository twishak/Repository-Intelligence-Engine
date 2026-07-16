# Codebase Understanding Agent

An agent that ingests a real codebase and answers natural-language questions
about it ("Where is X handled?", "Explain what this function does", "What
would break if I changed Y?") using retrieval-grounded answers rather than
hallucinated guesses.

## Stack

- **Orchestration:** LangGraph (explicit state graph, not chained prompts)
- **LLM:** Groq API (`llama-3.3-70b-versatile` by default)
- **Vector store:** Chroma (local, embedded, persistent)
- **Embeddings:** local, via `sentence-transformers` (code-aware model)

See [`docs/adr/`](docs/adr/README.md) for the architectural decisions behind this design and why - notably why
this isn't just a RAG chatbot ([ADR-0001](docs/adr/0001-hybrid-repository-intelligence-over-pure-rag.md)) and why
it's Python-only for now ([ADR-0002](docs/adr/0002-python-first-before-multi-language-expansion.md)).

## Status

End-to-end and working: ingestion -> chunking -> embedding/storage -> retrieval
-> LangGraph orchestration -> LLM reasoning -> CLI interface.

The orchestration graph is a one-shot pipeline (`route_question -> retrieve ->
generate_answer`), not an agentic tool-calling loop: a single LLM call picks
one of three retrieval strategies (`semantic_search`, `find_by_qualified_name`,
`find_references`), that strategy runs once, and a second LLM call answers
using only the retrieved chunks, citing `file:start-end` for every claim.
Multi-step retrieval (e.g. chaining strategies for one question) is a
possible V2, not implemented yet.

**Repository Intelligence** (`codebase_agent.intelligence`): a second,
independent pipeline built alongside the chunker. `ast`-based extraction
produces a repo-wide symbol table plus import/call/class-hierarchy graphs
(`networkx`), persisted per-repo as JSON under `data/graph/<repo>/`. Call and
inheritance resolution is best-effort static matching (self./cls. attributes,
exact qualified names, then unambiguous short-name fallback preferring the
same file) - unresolved edges are kept, not dropped, marked with a `None`
qualified name. Runs automatically as part of `scripts/ingest_repo.py`; not
yet wired into retrieval or the agent (that's a later step).

**Knowledge Layer** (`codebase_agent.knowledge`): the single access boundary
every higher-level subsystem (retrieval, the agent, developer insights, the
CLI, the future REST API) will depend on - none of them talk to Chroma,
NetworkX, or JSON files directly. `KnowledgeBase` (a `Protocol`) is the
contract; `DefaultKnowledgeBase` is the implementation, composing the
Repository Intelligence symbol table/edges, persisted per-symbol source
snippets (`sources.json`, sliced at ingestion time so lookups don't depend on
the checkout still being on disk), the vector store, and per-repo metadata
(`RepoMetadata`, including a `schema_version` checked at load time so stale
pre-Knowledge-Layer or format-incompatible artifacts fail clearly with a
"re-ingest" error instead of silently misbehaving). `KnowledgeBaseFactory`
builds instances; `KnowledgeBaseRegistry` caches them per repo so repeated
lookups don't reload from disk - construction and lifecycle are deliberately
separate classes. The interface is intentionally atomic (symbol/caller/
callee/import/inheritance lookups, semantic search, metadata) - no ranking,
no multi-hop composition, no hybrid retrieval; those are the Retrieval
Layer's job, built by composing these primitives, not implemented yet.

**Reasoning Retrieval Engine** (`codebase_agent.retrieval`): gathers
evidence, never generates prose. `RetrievalPlanner` (one Groq tool-calling
call, no `KnowledgeBase` access) turns a question into a `RetrievalPlan` -
one or more `RetrievalStep`s naming a strategy (`symbol_lookup`,
`semantic_search`, `call_graph`, `import_graph`, `hierarchy`) plus target/
query/direction; compound intents like impact analysis become multiple steps
(resolve the symbol, then walk its callers) rather than a new strategy.
`RetrievalExecutor` dispatches each step to a specialized retriever
(`retrieval/retrievers/`), all reading through `KnowledgeBase` only, and
aggregates the results into an `EvidenceBundle` - `EvidenceItem`s carry a
normalized shape (`qualified_name`/`file_path`/`start_line`/`end_line`/
`content`/`explanation`/`confidence`), not the underlying `Symbol`/`CallEdge`/
etc. objects, keeping Evidence itself as the abstraction boundary. A failing
or unregistered step is recorded as a warning and skipped, not fatal - the
bundle also carries `retrievers_used`, `warnings`, and `execution_time_seconds`
for debugging. This is a new, parallel pipeline: `graph/*.py` (the LangGraph
pipeline) and the legacy `CodeRetriever` are untouched and still power the
CLI today.

**Reasoning Engine** (`codebase_agent.reasoning`): turns an `EvidenceBundle`
into a grounded, citation-aware `ReasoningResult` - never the other way
around. LangGraph here is purely sequencing (`plan_retrieval ->
execute_retrieval -> reason`, one pass, no cycles, no conditional edges,
no tool-calling loop), composing the existing `RetrievalPlanner` /
`RetrievalExecutor` from the retrieval engine without changing them.
`ReasoningEngine` makes one forced Groq tool call over all the evidence at
once; citations are index-based - the model names which numbered evidence
item(s) it used, and the exact `file_path`/`start_line`/`end_line` are
resolved from the `EvidenceBundle` in Python, not transcribed by the LLM, so
citation accuracy doesn't depend on the model getting numbers right.
`AnswerValidator` then runs a handful of deterministic, non-LLM checks
(hallucinated citation indices, empty answers, "sufficient" claimed against
zero evidence) and attaches any issues to the result - informational only,
nothing here retries or re-prompts. Prompts live as external text files
under `reasoning/prompts/` (loaded via `string.Template`, not `str.format`,
so literal `{}` in evidence/code snippets can't break substitution), tagged
with a `prompt_version` on every result for future evaluation. `ReasoningResult`
also carries `confidence`, `evidence_sufficient`, `assumptions` (inferences
not directly confirmed), and `limitations` (known gaps in the evidence
itself) as separate fields, rather than folding everything into prose.
This is additive alongside the legacy pipeline too: `graph/*.py` and
`CodeRetriever` are still untouched. `scripts/ask_v2.py` runs the new
pipeline standalone for side-by-side comparison against `scripts/ask.py`
before any decision to deprecate the old one.

**Repository Insights** (`codebase_agent.insights`): deterministic, LLM-free
repository analysis - five independent `Analyzer`s (dead code, circular
dependencies, complexity, TODO/FIXME, architecture), each depending only on
`KnowledgeBase` and never calling each other. `AnalysisRunner` dispatches
each and aggregates results into a `RepositoryReport` - the canonical output
meant for the CLI, a future REST API, and Markdown/JSON export - containing
repo metadata, generic repo-wide statistics (file/symbol/edge counts,
independent of any analyzer), normalized `Finding`s (one shape for all five
analyzers, same "normalize at the boundary" approach as `EvidenceItem`), and
a `summary: str | None` placeholder reserved for a future LLM-generated
repository summary built on top of this report, not part of this subsystem.
Findings get a stable, deterministic `id` so the same issue matches across
re-analysis runs. Required extending `KnowledgeBase` with generic whole-repo
primitives (`all_symbols`, `all_import_edges`, `all_call_edges`,
`all_inherits_edges`, `get_file_source`) - deliberately generic, not
analyzer-specific methods. `scripts/analyze_repo.py` runs the analyzers and
prints the report. See [`docs/adr/`](docs/adr/README.md) for the full
rationale behind every decision above.

**Presentation Layer** (`codebase_agent.application`, `codebase_agent.api`,
`codebase_agent.cli`): exposes everything above without adding new business
logic. Four `Application Service`s (`IngestionService`, `ReasoningService`,
`InsightsService`, `RepositoryService`) are the *only* thing the CLI and
FastAPI depend on - neither ever imports `intelligence`, `knowledge`,
`retrieval`, `reasoning`, or `insights` directly. Services return the same
dataclasses those subsystems already produce (`RepoMetadata`,
`ReasoningResult`, `RepositoryReport`); a small `ApplicationError` hierarchy
(`RepositoryNotFoundError`, `RepositoryIncompatibleError`,
`IngestionFailedError`) is what CLI/API actually catch, translated once at
the service boundary from lower-layer exceptions. Pydantic request/response
schemas (`api/schemas.py`, with `from_domain()` converters and OpenAPI
examples on request bodies) exist only at the FastAPI boundary - the CLI
renders the same dataclasses directly with Rich, no Pydantic involved.
`KnowledgeBaseRegistry`/embedder/Groq-client singletons live once on
`app.state` (attached at startup), not reconstructed per request - services
are cheap and built fresh per request from those shared singletons via
`Depends()`. Every API request gets a `uuid4` id (via a contextvar, so any
log line anywhere during that request's handling picks it up automatically,
no threading required) surfaced as `X-Request-ID`, in structured log lines,
and in error response bodies - enough to correlate one request's logs, not
distributed tracing. `graph/*.py`, `CodeRetriever`, `interface/cli.py`, and
all four existing scripts stay completely untouched; this is a new sibling
layer, not a replacement.

## Setup

```
pip install -r requirements.txt
cp .env.example .env   # then fill in GROQ_API_KEY
```

Install `torch` separately with the CUDA build matching your GPU driver
before installing `sentence-transformers`'s other dependencies, see
https://pytorch.org/get-started/locally/.

## Usage

Ingest a repository (local path or git URL):

```
python scripts/ingest_repo.py /path/to/repo
python scripts/ingest_repo.py https://github.com/user/repo.git
```

Ask questions about it:

```
python scripts/ask.py <repo-name>                        # interactive REPL
python scripts/ask.py <repo-name> -q "Where is X handled?"  # single question
python scripts/ask.py --list                              # list ingested repos
```

`<repo-name>` is the directory/repo name used at ingestion time (e.g. the
folder name for a local path, or the repo name for a git URL).

To try the new evidence-driven reasoning engine instead of the legacy
pipeline, use `scripts/ask_v2.py` the same way:

```
python scripts/ask_v2.py <repo-name> -q "What would break if I changed X?"
```

To run repository analysis (dead code, circular dependencies, complexity, TODOs, architecture):

```
python scripts/analyze_repo.py <repo-name>
python scripts/analyze_repo.py <repo-name> --category dead_code
```

The new CLI (Typer-based, calls the Application Services) wraps all of the above in one entry point:

```
python scripts/cli.py ingest /path/to/repo
python scripts/cli.py list
python scripts/cli.py info <repo-name>
python scripts/cli.py ask <repo-name> "What would break if I changed X?"
python scripts/cli.py analyze <repo-name> --category dead_code
```

To run the REST API (interactive docs at `/docs`, OpenAPI schema at `/openapi.json`):

```
python scripts/serve_api.py
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) and [NOTICE](NOTICE).
