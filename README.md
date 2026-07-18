# Repository Intelligence Engine

*(working name - the public repo name isn't finalized yet)*

A software intelligence platform for codebases: static analysis (symbol tables, call/import/inheritance graphs),
grounded and citation-backed question answering, and deterministic repository analysis (dead code, circular
dependencies, complexity, architecture), exposed through a REST API and a CLI.

Ask it things like *"Where is X handled?"*, *"Explain what this function does"*, or *"What would break if I changed
Y?"* and get an answer grounded in retrieved evidence, with citations back to exact file/line ranges - not a
hallucinated guess.

- **Static analysis:** `ast`-based symbol table plus call/import/class-hierarchy graphs, independent of any LLM.
- **Grounded Q&A:** evidence is retrieved first, then reasoned over; every claim is cited or the answer says so.
- **Deterministic analysis:** dead code, circular dependencies, complexity, TODOs, and architecture findings - no
  LLM involved, same input always produces the same findings.
- **REST API and CLI:** both are thin wrappers over the same Application Service layer - no logic duplicated
  between them.

**Stack:** static analysis via `ast` + `networkx` · orchestration via LangGraph (deterministic pipelines, not an
agentic loop - see [ADR-0009](docs/adr/0009-deterministic-single-pass-orchestration.md)) · LLM via the Groq API ·
vector store via local, embedded Chroma · embeddings via local `sentence-transformers` · API via FastAPI · CLI via
Typer.

See [`docs/architecture.md`](docs/architecture.md) for how the layers fit together, and
[`docs/adr/`](docs/adr/README.md) for the reasoning behind each design decision.

## Quick Start

Requires Python 3.10+ and a [Groq API key](https://console.groq.com/keys).

```bash
git clone <this-repo>
cd <this-repo>

pip install -r requirements.lock   # exact, tested versions (use requirements.txt for a fresh resolve)
pip install -e .                   # registers the `codebase-agent` command

cp .env.example .env               # then fill in GROQ_API_KEY
```

Install `torch` separately first with the CUDA build matching your GPU driver if you want GPU-accelerated
embeddings - see https://pytorch.org/get-started/locally/. Otherwise a CPU-only build installs automatically as a
dependency of `sentence-transformers`. If ingestion hits a CUDA out-of-memory error, lower `EMBEDDING_BATCH_SIZE`
in `.env` (see `.env.example`); if that's still not enough (a single very large chunk can be memory-heavy on its
own), set `EMBEDDING_DEVICE=cpu`.

```bash
codebase-agent ingest <path-or-git-url>
codebase-agent ask <repo-name> "<question>"
codebase-agent analyze <repo-name>
```

Example session, ingesting the tiny demo repo that ships in [`examples/demo`](examples/demo) (a 3-file in-memory
task manager with one genuinely unused function) - run this yourself right after cloning, no external repo needed:

```text
$ codebase-agent ingest examples/demo
demo
  files: 3
  symbols: 8
  schema_version: 1

$ codebase-agent ask demo "What does complete_task do?"
The complete_task function marks a task complete by updating its status to True
in the _tasks dictionary. It takes a slug as input and raises a KeyError if the
task does not exist. [1]

confidence=high evidence_sufficient=True
Citations:
  [1] tasks.TaskManager.complete_task (tasks.py:18-21)

$ codebase-agent analyze demo
Statistics
  files=3 symbols=8 (functions=3 methods=4 classes=1)
  call_edges=6 (resolved=2) import_edges=2 (resolved=2) inherits_edges=0

Findings by category
  architecture: 2
  dead_code: 5
```

`reporting.summarize_counts` (a function nothing else in the demo repo calls) is correctly flagged under
`dead_code` - all of the above is real, unedited tool output.

Run the REST API instead of the CLI:

```bash
python scripts/serve_api.py
```

Then open `http://127.0.0.1:8000/docs` for interactive Swagger docs, or `/openapi.json` for the raw schema.

*(A screenshot of the Swagger UI belongs here - not yet captured.)*

## How it works

Six layers, each depending only on the one below it through a narrow interface:

**Repository Intelligence** → **Knowledge Layer** → **Reasoning Retrieval Engine** → **Reasoning Engine** /
**Repository Insights** → **Presentation Layer** (CLI + REST API)

Full explanation, with diagrams, in [`docs/architecture.md`](docs/architecture.md). The short version: static
analysis and embeddings both feed a single `KnowledgeBase` access boundary; retrieval gathers evidence but never
writes prose; reasoning turns evidence into a cited answer and never the reverse; insights runs deterministic,
LLM-free analyzers; and the CLI/API only ever call into an Application Service layer, never the lower layers
directly.

A separate legacy pipeline (`scripts/ask.py`, `codebase_agent.graph`) predates this design and is kept in place,
untouched, rather than deleted - see the Legacy pipeline section of the architecture doc.

## Development

```bash
pip install -r requirements.lock
pip install -e .

ruff check .            # lint
ruff format --check .   # format check
pytest -m "not integration"   # full suite, no real API/model calls
pytest -m integration         # slower tests hitting the real Groq API and embedding model
```

CI (`.github/workflows/ci.yml`) runs lint, format check, and the non-integration test suite on every push/PR.

## License

Apache License 2.0 - see [LICENSE](LICENSE) and [NOTICE](NOTICE).
