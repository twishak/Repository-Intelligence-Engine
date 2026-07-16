# 0004. Best-Effort Symbol Resolution: Keep Unresolved Edges, Never Drop Them

## Status

Accepted

## Context

Python's dynamism (duck typing, `getattr`, decorators, monkeypatching, metaclasses) means a fully sound static call
graph is impossible. Every call/import/inheritance extractor has to choose what happens when it can't resolve a
reference: silently drop it, guess, or keep it as an explicitly-unresolved fact.

## Decision

Every edge type (`CallEdge`, `ImportEdge`, `InheritsEdge`) always records the raw reference (`callee_name`,
`imported_module`, `base_name`) and separately records the resolution (`callee_qualified_name`, `resolved_file`,
`base_qualified_name`), which is `None` when resolution fails - the edge is kept, not dropped. Resolution itself is
layered: exact qualified-name match, then same-file short-name match, then unambiguous repo-wide short-name match;
anything still ambiguous or external is left unresolved rather than guessed at.

## Consequences

Downstream consumers must handle `None` qualified names as a first-class case, not an edge case - and they do,
deliberately: Retrieval's confidence scoring
([0008](0008-retrieval-as-planning-and-execution.md)) treats unresolved edges as lower-confidence evidence instead
of hiding them; the Reasoning Engine's evidence-sufficiency signal
([0009](0009-deterministic-single-pass-orchestration.md)) can reflect that some referenced code wasn't statically
resolvable; Insights' dead-code analyzer ([0014](0014-independent-composable-analyzers.md)) explicitly caveats its
findings because "no resolved callers" is not the same claim as "no callers." A system that silently dropped
unresolved edges would look more confident and be less honest.
