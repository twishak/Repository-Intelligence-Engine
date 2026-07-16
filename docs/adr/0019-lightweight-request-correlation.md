# 0019. Lightweight Request Correlation via Context-Local Request IDs, Not Distributed Tracing

## Status

Accepted

## Context

A server handling concurrent requests interleaves log output from all of them in one stream. Without some way to
tell "these log lines belong to the same request," debugging a single failed call means guessing from timestamps
and content. Full distributed tracing (span propagation, a tracing backend) solves this and more, but is real
infrastructure - a genuine new capability, not just exposing existing ones, and overkill for a single-process API
with no downstream services to trace into.

## Decision

Each request gets a `uuid4` id, generated in `RequestIdMiddleware` and stored in a `contextvars.ContextVar` for the
duration of that request's handling. A `logging.Filter` (`RequestIdLogFilter`) reads the contextvar and injects it
into every log record emitted while the context is active - which means services, retrieval, reasoning, and
insights code all get request-correlated logs automatically, without any of those modules being changed to accept
or thread through a request id. The id is also returned as an `X-Request-ID` response header and included in
`ApplicationError` JSON response bodies ([0017](0017-application-level-exception-translation.md)), so a
client-visible error can be matched back to server logs without needing header access.

## Consequences

Grepping one request's log lines out of a busy server is a single `grep <request-id>` - verified directly against
real log output during testing, where a single ingest request's logs consistently carried one id across the
ingestion service, the embedder, and sentence-transformers' own logging, none of which know anything about request
ids. This is correlation, not tracing - there's no span hierarchy, no cross-service propagation, and no timing
breakdown beyond what's already in `ReasoningResult.reasoning_time_seconds` /
`EvidenceBundle.execution_time_seconds` / `RepositoryReport.execution_time_seconds`. If this system ever gains
genuinely distributed components, this mechanism would need to be replaced, not extended.
