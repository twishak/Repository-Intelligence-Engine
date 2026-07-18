# Repository Insights

Deterministic, LLM-free repository analysis. For where this fits among the other layers, see the Repository
Insights section of [`architecture.md`](architecture.md) - this document goes one level deeper on what each
analyzer finds and what the output looks like.

## Why deterministic, and why that matters

Five independent `Analyzer`s - dead code, circular dependencies, complexity, TODO/FIXME, architecture - each depend
only on `KnowledgeBase` and never call each other or an LLM
([ADR-0014](adr/0014-independent-composable-analyzers.md)). The same repository, analyzed twice, always produces
the same findings. That's not incidental - it's what makes the output reproducible across commits, diffable in a
PR, and safe to run unattended in CI, none of which is true of an LLM's opinion on the same code.

## What each analyzer finds

| Category | What it finds |
|---|---|
| Dead code | Symbols with no resolved callers anywhere in the repo - may be genuinely unused, or invoked dynamically/externally (a CLI entry point, a framework callback, a test discovered by name); flagged for verification, not assumed dead |
| Circular dependencies | Import cycles between modules |
| Complexity | Functions/methods that are unusually large or branchy |
| TODO / FIXME | Outstanding markers left in comments |
| Architecture | Structural findings - e.g. a module with unusually high fan-in, or a layering violation |

`AnalysisRunner` dispatches each analyzer and aggregates the results into a `RepositoryReport` - the canonical
output consumed by both the CLI and the REST API. It contains:

- Repo metadata (name, ingestion time, schema version)
- Generic repo-wide statistics, independent of any single analyzer: `total_files`, `total_symbols`,
  `function_count`, `method_count`, `class_count`, `total_import_edges`, `total_call_edges`,
  `total_inherits_edges`, `resolved_call_edges`, `resolved_import_edges`
- Normalized `Finding`s - one shape for all five analyzers (same "normalize at the boundary" approach used for
  retrieval evidence, [ADR-0007](adr/0007-normalized-structured-outputs-at-layer-boundaries.md))
- A `summary: str | None` field, currently always `None` - reserved for a future LLM-generated repository summary
  built on top of this report (see the Roadmap in the README)

Each `Finding` carries a stable, deterministic `id` (derived from its content, not assigned sequentially), so the
same issue matches across re-analysis runs instead of getting a new identity every time.

## Full REST example

```bash
curl http://127.0.0.1:8000/v1/repositories/demo/insights
```

Real, unedited response (trimmed to one representative finding per category; the full response lists all findings):

```json
{
  "repo_name": "demo",
  "statistics": {
    "total_files": 3,
    "total_symbols": 8,
    "function_count": 3,
    "method_count": 4,
    "class_count": 1,
    "total_import_edges": 2,
    "total_call_edges": 6,
    "total_inherits_edges": 0,
    "resolved_call_edges": 2,
    "resolved_import_edges": 2
  },
  "finding_counts": {"dead_code": 5, "architecture": 2},
  "findings": [
    {
      "id": "d76acde841f6",
      "category": "dead_code",
      "severity": "warning",
      "title": "No callers found for 'tasks.TaskManager.complete_task'",
      "description": "method 'tasks.TaskManager.complete_task' has no resolved callers in the static call graph. This may be dead code, or it may be invoked dynamically or externally (a CLI entry point, a framework callback, a test discovered by name, an exported public API) - verify before removing.",
      "qualified_name": "tasks.TaskManager.complete_task",
      "file_path": "tasks.py",
      "start_line": 18,
      "end_line": 21,
      "details": {"kind": "method"}
    },
    {
      "id": "322fd2b7c589",
      "category": "architecture",
      "severity": "info",
      "title": "'utils.py' is imported by 2 file(s)",
      "description": "'utils.py' has high fan-in (2 importers), suggesting it's a structurally central module.",
      "qualified_name": null,
      "file_path": "utils.py",
      "start_line": null,
      "end_line": null,
      "details": {"importer_count": 2}
    }
  ],
  "warnings": [],
  "execution_time_seconds": 0.0019251999983680435
}
```

`reporting.summarize_counts` in `examples/demo` - a function nothing else in that repo calls - is one of the five
real `dead_code` findings behind `finding_counts` above.

## See also

- [`architecture.md`](architecture.md) - how Repository Insights fits among the other layers
- [ADR-0014](adr/0014-independent-composable-analyzers.md) - why analyzers are independent and composable
- [`cli-and-api.md`](cli-and-api.md) - the `analyze` CLI command and the full REST reference
