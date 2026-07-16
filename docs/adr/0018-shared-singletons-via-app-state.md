# 0018. Shared Long-Lived Singletons via app.state, Services Rebuilt per Request

## Status

Accepted

## Context

`KnowledgeBaseRegistry` exists specifically to cache a `KnowledgeBase` per repo so repeated lookups don't reload
the symbol table from disk ([0005](0005-knowledgebase-as-the-sole-access-boundary.md)). FastAPI's idiomatic
`Depends()` pattern makes it easy to accidentally construct a fresh dependency on every request - which for
`KnowledgeBaseRegistry`, `CodeEmbedder`, or `GroqClient` would silently defeat their own caching/lazy-loading and
rebuild expensive state on every single API call.

## Decision

The genuinely expensive, stateful resources - `KnowledgeBaseRegistry`, `CodeEmbedder`, `CodeVectorStore`, and the
`RetrievalPlanner` / `RetrievalExecutor` / `ReasoningEngine` / `AnalysisRunner` built from them - are constructed
once, in a FastAPI `lifespan` handler, and attached to `app.state`. The four Application Services
([0015](0015-application-service-layer-as-the-sole-boundary.md)) are cheap, stateless wrappers around those
singletons and are constructed fresh per request via `Depends()` functions in `api/dependencies.py`, each pulling
the shared singletons off `request.app.state`.

## Consequences

`KnowledgeBaseRegistry`'s cache actually works as designed across the life of the server process, not just within
a single request. Tests don't need the real singletons at all - route tests override the `get_*_service`
dependency functions directly with fakes, bypassing `app.state` entirely, so most API tests never trigger real
model loading or Groq calls. The cost: two different dependency-construction patterns to keep straight (module-level
singletons on `app.state` vs. per-request service construction) - documented explicitly in `dependencies.py` so the
distinction doesn't get blurred as new endpoints are added.
