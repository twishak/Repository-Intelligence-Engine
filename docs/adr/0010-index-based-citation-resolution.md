# 0010. Index-Based Citation Resolution for Trustworthy Grounding

## Status

Accepted

## Context

For citations (file path, line numbers) to be useful, they have to be *correct* - a plausible-looking but wrong
line number is worse than no citation, because it looks trustworthy while being wrong. Asking the LLM to transcribe
exact file paths and line numbers into its structured output risks exactly that: transcription errors, especially
from smaller/faster models, that would be silently wrong rather than obviously wrong.

## Decision

Evidence shown to the reasoning LLM is numbered (`[1]`, `[2]`, ...); the LLM's structured output cites evidence by
that integer index, not by re-stating file/line data. `ReasoningEngine` then resolves each cited index back to the
exact `file_path` / `start_line` / `end_line` already present in the `EvidenceBundle`
([0007](0007-normalized-structured-outputs-at-layer-boundaries.md)) - Python does the lookup, not the model.
Indices outside the valid range are kept in `cited_evidence_indices` (not silently dropped) and flagged by the
deterministic validator ([0012](0012-deterministic-non-llm-answer-validation.md)) as a hallucinated citation.

## Consequences

Every citation that survives into `ReasoningResult.citations` is guaranteed accurate by construction - there's no
code path where a citation's location doesn't match real evidence. The trade-off is that the model can still cite
the *wrong* evidence item (index 3 when it meant to rely on index 5) - this scheme guarantees location accuracy,
not relevance accuracy, which no deterministic check can fully catch.
