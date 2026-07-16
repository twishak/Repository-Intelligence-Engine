# 0012. Deterministic, Non-LLM Answer Validation over Self-Correcting Re-Prompting

## Status

Accepted

## Context

Having generated a `ReasoningResult`, a second LLM call could "grade" or self-correct the answer against the
evidence - but that reintroduces an iteration loop that
[0009](0009-deterministic-single-pass-orchestration.md) explicitly avoids, doubles LLM cost and latency per
question, and adds another source of hallucination (a grading LLM can be wrong too).

## Decision

`AnswerValidator` runs a small set of cheap, deterministic, non-LLM checks against the `ReasoningResult` and the
`EvidenceBundle` it came from: cited indices that don't exist in the evidence
([0010](0010-index-based-citation-resolution.md)), an `evidence_sufficient=True` claim against zero retrieved
evidence, an empty answer, and a sufficiency claim with no citations at all. Results are attached to
`ReasoningResult.validation_issues` and are purely informational - nothing here triggers a retry or re-prompt.

## Consequences

Validation is fast, free, and fully deterministic (same input always produces the same issues), but is deliberately
narrow - it catches obvious mechanical inconsistencies, not semantic correctness (e.g. it cannot tell whether the
prose answer actually reflects what the cited evidence says). A more thorough validator (e.g. checking that
qualified names mentioned in the prose appear somewhere in the evidence) was considered and explicitly deferred as
too failure-prone with simple string matching.
