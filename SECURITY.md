# Security Policy

## Supported versions

Pre-1.0: only the `main` branch is supported. Once a `1.0.0` tag exists, security fixes will target the latest
released minor version.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security vulnerability. Use GitHub's private vulnerability
reporting instead: go to the repository's **Security** tab → **Report a vulnerability**. This opens a private
advisory visible only to the maintainer until a fix is ready.

Include what you'd include in any vulnerability report: the affected component, reproduction steps or a PoC, and
the impact you'd expect. Expect an initial response within a few days - this is currently a solo-maintained
project.

## Project-specific risk notes

A few things about how this system behaves that are worth knowing before deploying it, beyond generic advice:

- **The REST API has no built-in authentication or authorization.** `scripts/serve_api.py` binds to
  `127.0.0.1` by default (see `API_HOST`/`API_PORT` in `.env.example`). If you expose it beyond localhost -
  behind a reverse proxy, in a container reachable from a network, etc. - put your own auth layer in front of it.
  Anyone who can reach it can ingest repositories, ask questions, and run analysis.
- **Ingesting a git URL clones untrusted code to local disk.** The ingestion pipeline only ever *parses* that code
  with `ast` (never executes it) to build the symbol table and graphs, and chunks/embeds the source text - it does
  not run the target repository's code, build scripts, or hooks. Cloning itself still carries the usual risks of
  running `git clone` against a URL you don't control (disk usage from a very large or malicious repo, for
  instance) - don't ingest sources you don't trust at least that far.
  See [ADR-0002](docs/adr/0002-python-first-before-multi-language-expansion.md) and
  [ADR-0003](docs/adr/0003-ast-based-extraction-over-tree-sitter.md) for why static parsing was chosen over any
  approach that would need to execute code.
- **Source code content is sent to the Groq API** as part of retrieval and reasoning (`GROQ_API_KEY` in
  `.env.example`). Don't ingest confidential or proprietary code unless that's consistent with your own data
  handling requirements and Groq's terms - this project doesn't add any additional redaction or filtering before
  sending evidence to the LLM.
- **`.env` (and any file containing `GROQ_API_KEY`) should never be committed.** It's excluded via `.gitignore`;
  double-check before force-adding anything.
