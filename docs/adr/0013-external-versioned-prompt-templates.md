# 0013. External, Versioned Prompt Templates

## Status

Accepted

## Context

The legacy pipeline (`graph/router.py`, `graph/answer.py`) embeds its system prompts as Python string constants.
That's fine for a short prompt that never changes, but the Reasoning Engine's grounding rules (evidence-only, cite
inline, report conflicts, separate assumptions from facts - see
[0009](0009-deterministic-single-pass-orchestration.md) and [0010](0010-index-based-citation-resolution.md)) are
exactly the kind of prompt text expected to be iterated on independently of application logic, especially once
evaluation against real questions starts surfacing prompt weaknesses.

## Decision

`reasoning/prompts/system_prompt.txt` and `user_prompt.txt` are plain text files, loaded at runtime and filled in
via `string.Template` (`$question` / `$evidence`) rather than `str.format()` - chosen specifically so a prompt
containing literal `{}` (an example JSON shape, or evidence content that happens to include a dict literal) can't
break substitution. Every `ReasoningResult` carries a `prompt_version` string, bumped whenever the prompt text
changes meaningfully, so future evaluation can group results by which prompt produced them. The tool-calling JSON
schema itself (`_REASONING_TOOL` in `engine.py`) deliberately stays in Python, not externalized alongside the
prose - a schema/parser mismatch fails silently or throws deep in JSON parsing, so the two must change together.

## Consequences

Prompt iteration doesn't require touching `engine.py` (or redeploying application code, if this were ever split
that way) - a real practical win once prompt tuning starts. The `prompt_version` field is currently a
manually-maintained constant, not automatically derived from the file contents (e.g. a hash) - a deliberate
simplicity choice that puts the burden on remembering to bump it, acceptable at current scale but worth revisiting
if prompt changes become frequent.
