# toy-tasks

A deliberately tiny (3-file) demo repo, used as the Quick Start example in the project README. Not a real
project - just enough structure (a class, a couple of helper functions, and one function nothing calls) to
demonstrate ingestion, grounded Q&A, and dead-code detection against something a reader can ingest immediately
without bringing their own codebase.

```bash
codebase-agent ingest examples/toy-tasks
codebase-agent ask toy-tasks "What does complete_task do?"
codebase-agent analyze toy-tasks
```
