# CLI and REST API Reference

Both interfaces are thin wrappers over the same four Application Services (`IngestionService`, `ReasoningService`,
`InsightsService`, `RepositoryService`) - see the Presentation Layer section of
[`architecture.md`](architecture.md). Nothing here
duplicates logic between them; this document just lists every command and route.

## CLI

```bash
codebase-agent ingest <path-or-git-url>          # ingest a local path or git URL
codebase-agent list                              # list ingested repositories
codebase-agent info <repo-name>                  # show metadata for one
codebase-agent ask <repo-name> "<question>"       # grounded, cited Q&A
codebase-agent ask <repo-name> "<question>" \
    --active-file src/app.py --active-symbol App  # optional IDE-style grounding
codebase-agent analyze <repo-name>                # run all 5 insight analyzers
codebase-agent analyze <repo-name> --category dead_code
```

| Command | Purpose | Notable options |
|---|---|---|
| `ingest <source>` | Ingest a local path or git URL | - |
| `list` | List ingested repositories | - |
| `info <repo-name>` | Show metadata for one ingested repository | - |
| `ask <repo-name> "<question>"` | Ask a grounded, cited question | `--active-file`, `--active-symbol` (grounding hints, see [Question Answering](question-answering.md)) |
| `analyze <repo-name>` | Run all 5 [Repository Insights](repository-insights.md) analyzers | `--category` (restrict to one: `dead_code`, `circular_dependency`, `complexity`, `todo`, `architecture`) |

Errors surface as a single red line and a non-zero exit code (`ApplicationError` translated at the CLI boundary,
[ADR-0017](adr/0017-application-level-exception-translation.md)) - no raw tracebacks for expected failure modes
like "repository not found."

## REST API

```bash
python scripts/serve_api.py
```

Interactive Swagger docs at `http://127.0.0.1:8000/docs`, raw OpenAPI schema at `/openapi.json`. Every request gets
a `uuid4` request id, surfaced as an `X-Request-ID` response header and in structured log lines
([ADR-0019](adr/0019-lightweight-request-correlation.md)).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/repositories` | List ingested repositories |
| `POST` | `/v1/repositories` | Ingest a repository (`{"source": "<path-or-git-url>"}`) |
| `GET` | `/v1/repositories/{repo_name}` | Get metadata for one repository |
| `POST` | `/v1/repositories/{repo_name}/questions` | Ask a grounded question (`{"question": "...", "active_file": null, "active_symbol": null}`) |
| `GET` | `/v1/repositories/{repo_name}/insights` | Run the 5 deterministic analyzers |

### Ingest

```bash
curl -X POST http://127.0.0.1:8000/v1/repositories \
  -H "Content-Type: application/json" \
  -d '{"source": "examples/demo"}'
```

`201 Created`, returning a `RepositoryMetadataResponse`. Field values below are the real, verified metadata for
`examples/demo` (same numbers shown in the CLI ingest output in the README's Demo section):

```json
{
  "repo_name": "demo",
  "source": "examples/demo",
  "ingested_at": "2026-07-18T17:19:38.894353+00:00",
  "file_count": 3,
  "symbol_count": 8,
  "schema_version": 1,
  "summary": null
}
```

### Ask a question

```bash
curl -X POST http://127.0.0.1:8000/v1/repositories/demo/questions \
  -H "Content-Type: application/json" \
  -d '{"question": "What does complete_task do?"}'
```

Real, unedited response - full field-by-field breakdown of the answer shape, retry behavior, and citation
resolution in [`question-answering.md`](question-answering.md):

```json
{
  "question": "What does complete_task do?",
  "answer": "The function complete_task marks a task as complete by setting the second element of the tuple associated with the task's slug in the _tasks dictionary to True. It raises a KeyError if the task does not exist. [1]",
  "confidence": "high",
  "evidence_sufficient": true,
  "assumptions": [],
  "limitations": [],
  "citations": [
    {
      "evidence_index": 1,
      "qualified_name": "tasks.TaskManager.complete_task",
      "file_path": "tasks.py",
      "start_line": 18,
      "end_line": 21,
      "source": "symbol"
    }
  ],
  "validation_issues": [],
  "model": "llama-3.3-70b-versatile",
  "prompt_version": "v1"
}
```

### Run the analyzers

```bash
curl http://127.0.0.1:8000/v1/repositories/demo/insights
```

Real, unedited response, trimmed - full analyzer-by-analyzer breakdown and the untrimmed example in
[`repository-insights.md`](repository-insights.md):

```json
{
  "finding_counts": {"dead_code": 5, "architecture": 2},
  "findings": [
    {
      "id": "d76acde841f6",
      "category": "dead_code",
      "severity": "warning",
      "title": "No callers found for 'tasks.TaskManager.complete_task'",
      "qualified_name": "tasks.TaskManager.complete_task",
      "file_path": "tasks.py",
      "start_line": 18,
      "end_line": 21
    }
  ]
}
```

## See also

- [Question Answering](question-answering.md) - the `ask` / `/questions` pipeline in depth
- [Repository Insights](repository-insights.md) - the `analyze` / `/insights` analyzers in depth
- [`architecture.md`](architecture.md) (Presentation Layer section) - why the CLI and API never contain their own logic
