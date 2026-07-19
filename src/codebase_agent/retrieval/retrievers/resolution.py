from codebase_agent.intelligence.models import Symbol
from codebase_agent.knowledge import KnowledgeBase

RESOLVED_CONFIDENCE = 1.0
UNRESOLVED_CONFIDENCE = 0.3
AMBIGUOUS_CONFIDENCE = 0.6


def resolve_symbol_candidates(
    kb: KnowledgeBase, target: str
) -> list[tuple[Symbol, float]]:
    """Best-effort resolution of a user/LLM-supplied name to known symbols.

    Tries an exact qualified-name match first (confidence 1.0), then falls
    back to a short-name match (confidence 1.0 if it's unambiguous, lower if
    several symbols share that short name - e.g. two classes each with a
    `run` method). For a partial dotted name like `Session.request` - a
    completely natural way to name a symbol, but neither the full qualified
    name (`requests.sessions.Session.request`) nor the bare short name
    (`request`) - falls back further to matching qualified names ending in
    `.<target>`. Steps that need a qualified name (call_graph, hierarchy)
    use this instead of requiring the planner/LLM to always supply an exact
    name up front.
    """
    exact = kb.get_symbol(target)
    if exact is not None:
        return [(exact, RESOLVED_CONFIDENCE)]

    matches = kb.find_symbols_by_name(target)
    if not matches and "." in target:
        matches = [
            symbol
            for symbol in kb.all_symbols()
            if symbol.qualified_name.endswith("." + target)
        ]
    if not matches:
        return []

    confidence = RESOLVED_CONFIDENCE if len(matches) == 1 else AMBIGUOUS_CONFIDENCE
    return [(symbol, confidence) for symbol in matches]


def resolve_file_path(kb: KnowledgeBase, target: str) -> str | None:
    """Resolve a file path or dotted module name to a known repo file path."""
    if target in kb.list_files():
        return target
    return kb.resolve_module(target)


def source_or(kb: KnowledgeBase, qualified_name: str | None, fallback: str) -> str:
    """The symbol's exact source text if known, else a short rendered fallback."""
    if qualified_name:
        source = kb.get_source(qualified_name)
        if source:
            return source
    return fallback
