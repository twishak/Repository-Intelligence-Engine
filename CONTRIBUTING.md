# Contributing

This is currently a solo-maintained project, but issues, questions, and pull requests are welcome.

## Development setup

See the [README Development section](README.md#development) for installing dependencies and running lint/tests.
The short version:

```bash
pip install -r requirements.lock
pip install -e .

ruff check . && ruff format --check . && pytest -m "not integration"
```

All three must pass before opening a PR. `pytest -m integration` also needs a real `GROQ_API_KEY` (see
`.env.example`) and downloads real model weights on first run - it's not required for most changes and isn't run
in CI, but run it yourself if you touched `reasoning/`, `retrieval/retrievers/semantic.py`, or `embeddings/`.

## Architecture discipline

Read [`docs/architecture.md`](docs/architecture.md) before making a non-trivial change. The project is built as
strict layers, each depending only on the layer directly below it through a narrow interface:

Repository Intelligence → Knowledge Layer → Reasoning Retrieval Engine → Reasoning Engine / Repository Insights →
Application Services → CLI / REST API

In particular:

- The CLI and API never call into `intelligence`, `knowledge`, `retrieval`, `reasoning`, or `insights` directly -
  only through an Application Service (`codebase_agent.application.services`).
- Retrieval gathers evidence; it never generates prose. Reasoning turns evidence into an answer; it never re-derives
  evidence on its own.
- Nothing above the Knowledge Layer talks to Chroma, NetworkX, or the persisted JSON artifacts directly - go
  through `KnowledgeBase`.
- The legacy pipeline (`codebase_agent.graph`, `codebase_agent.llm`, `codebase_agent.interface`, the legacy
  `CodeRetriever` in `codebase_agent.retrieval.retriever`, and `scripts/ask.py`) is left in place deliberately.
  Don't modify it as a side effect of an unrelated change - if it genuinely needs to change, say why in the PR.

If a change makes a real architectural decision (a new dependency direction, a new persisted format, a new
external boundary), add an [ADR](docs/adr/README.md) for it in Nygard format (Title, Status, Context, Decision,
Consequences), numbered sequentially, cross-referenced with related ADRs. Never edit an existing ADR's Decision or
Consequences to match a later change - write a new one and mark the old one `Superseded by NNNN`.

## Commit conventions

Commits follow [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, imperative
mood, under ~72 characters for the summary line.

```
feat(retrieval): add hierarchy retriever
fix(cli): register codebase-agent console script entry point
docs(adr): document repository insights architecture decision
refactor(application): extract shared knowledge-base lookup helper
test(reasoning): cover citation index resolution
chore(ci): add GitHub Actions workflow
```

Each commit should be one coherent, self-contained change - understandable in isolation from its diff and message
alone, not "implement retrieval, reasoning, CLI, docs and tests" as a single commit. Run lint, format, and the
relevant tests before each commit, not just before the final PR.

## Pull requests

- Keep PRs scoped to one change; split unrelated changes into separate PRs.
- Update `README.md`, `docs/architecture.md`, or an ADR alongside any change in behavior or design they describe -
  documentation should never trail the code it documents.
- Add or update tests for anything you change; don't rely on manual verification alone.
- Describe *why*, not just *what*, in the PR description - the "what" is already in the diff.

## Reporting bugs / requesting features

Open an issue describing the problem or proposal. For anything touching the architecture (new subsystem, new
dependency direction, new external integration), a short design discussion before implementation is preferred over
a large unreviewed PR - see how each feature in this project's git history was designed before being built.

## Security issues

Do not open a public issue for a security vulnerability - see [SECURITY.md](SECURITY.md).
