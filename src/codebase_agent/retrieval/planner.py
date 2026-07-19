import json
import logging
from dataclasses import dataclass

from codebase_agent.llm import GroqClient
from codebase_agent.retrieval.plan import (
    RetrievalPlan,
    RetrievalPriority,
    RetrievalStep,
    RetrievalStrategy,
)

logger = logging.getLogger(__name__)

_DIRECTIONS = (
    "callers",
    "callees",
    "bases",
    "subclasses",
    "imports",
    "importers",
    "both",
)

_PLANNER_TOOL = {
    "type": "function",
    "function": {
        "name": "build_retrieval_plan",
        "description": "Break the user's question about a codebase into one or more retrieval steps.",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": (
                        "Short label for the question's intent, e.g. 'impact_analysis', "
                        "'architecture_exploration' - for logging only."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Optional cap on total evidence items returned across all steps. Omit for no cap.",
                },
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "strategy": {
                                "type": "string",
                                "enum": [s.value for s in RetrievalStrategy],
                                "description": (
                                    "'symbol_lookup' when a specific function/method/class is named; "
                                    "'semantic_search' for open-ended/conceptual questions or broad "
                                    "topics like 'explain the architecture'; 'call_graph' for 'what "
                                    "calls X' / 'what would break if I changed X' (use direction "
                                    "'callers' for impact analysis); 'import_graph' for 'what does this "
                                    "file depend on' / 'what depends on this file'; 'hierarchy' for "
                                    "inheritance questions. Combine multiple steps for compound "
                                    "questions - e.g. impact analysis is a symbol_lookup step to "
                                    "resolve the target plus a call_graph step with direction='callers'."
                                ),
                            },
                            "target": {
                                "type": "string",
                                "description": (
                                    "Qualified or short symbol name (symbol_lookup, call_graph, "
                                    "hierarchy), file path or dotted module name (import_graph). "
                                    "Omit for semantic_search."
                                ),
                            },
                            "query": {
                                "type": "string",
                                "description": (
                                    "Free-text search query. Only used by semantic_search; omit otherwise."
                                ),
                            },
                            "direction": {
                                "type": "string",
                                "enum": list(_DIRECTIONS),
                                "description": (
                                    "call_graph: 'callers'|'callees'|'both'. hierarchy: "
                                    "'bases'|'subclasses'|'both'. import_graph: "
                                    "'imports'|'importers'|'both'. Omit for symbol_lookup/semantic_search."
                                ),
                            },
                        },
                        "required": ["strategy"],
                    },
                },
            },
            "required": ["steps"],
        },
    },
}

_SYSTEM_PROMPT = (
    "You plan how to gather evidence to answer questions about a codebase. "
    "Call build_retrieval_plan exactly once with one or more retrieval steps."
)


@dataclass(frozen=True)
class RetrievalContext:
    """Optional grounding for planning - e.g. what the user currently has
    open in an IDE. Only `repo_name` is required; the rest is forward-looking
    for later features (conversational planning, active-file/-symbol bias)
    and safe to leave unset today.
    """

    repo_name: str
    active_file: str | None = None
    active_symbol: str | None = None
    # Reserved for future conversational planning (prior Q&A turns) - not
    # used yet. Deciding how much history to feed the planner, and how to
    # summarize it, is a real design question left for when it's needed.
    conversation_history: tuple[str, ...] = ()


class RetrievalPlanner:
    """Classifies a question into a RetrievalPlan: one or more RetrievalSteps
    naming a specialized retriever and its parameters.

    A single LLM call, no KnowledgeBase access, no iterative reasoning -
    multi-step plans come from the LLM choosing several steps up front, not
    from looping. Iterative/agentic planning is a LangGraph-based feature,
    not this one.
    """

    def __init__(self, llm: GroqClient | None = None) -> None:
        self._llm = llm or GroqClient()

    def plan(
        self, question: str, context: RetrievalContext | None = None
    ) -> RetrievalPlan:
        message = self._llm.chat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_content(question, context)},
            ],
            tools=[_PLANNER_TOOL],
            tool_choice={
                "type": "function",
                "function": {"name": "build_retrieval_plan"},
            },
            # This is a classification decision (which strategy/target fits
            # the question), not creative generation - deterministic output
            # means the same question reliably gets the same plan instead of
            # occasionally sampling a plausible-but-wrong strategy or a
            # hallucinated symbol name.
            temperature=0,
        )
        return _parse_plan(message, question)


def _build_user_content(question: str, context: RetrievalContext | None) -> str:
    if context is None:
        return question

    hints = []
    if context.active_symbol:
        hints.append(f"the user is currently viewing symbol `{context.active_symbol}`")
    if context.active_file:
        hints.append(f"in file `{context.active_file}`")
    if not hints:
        return question

    return f"{question}\n\n(Context: {' and '.join(hints)}.)"


def _fallback_plan(question: str) -> RetrievalPlan:
    return RetrievalPlan(
        steps=(
            RetrievalStep(strategy=RetrievalStrategy.SEMANTIC_SEARCH, query=question),
        ),
        intent="fallback",
    )


def _parse_plan(message, question: str) -> RetrievalPlan:
    tool_calls = message.tool_calls or []
    if not tool_calls:
        logger.warning(
            "Planner returned no tool call - defaulting to a single semantic_search step"
        )
        return _fallback_plan(question)

    try:
        arguments = json.loads(tool_calls[0].function.arguments)
        raw_steps = arguments["steps"]
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(
            "Planner response malformed (%s) - defaulting to a single semantic_search step",
            e,
        )
        return _fallback_plan(question)

    steps = [
        step for step in (_parse_step(raw) for raw in raw_steps) if step is not None
    ]
    if not steps:
        logger.warning(
            "Planner produced no usable steps - defaulting to a single semantic_search step"
        )
        return _fallback_plan(question)

    max_results = arguments.get("max_results")
    if not isinstance(max_results, int) or max_results <= 0:
        max_results = None

    return RetrievalPlan(
        steps=tuple(steps),
        intent=arguments.get("intent"),
        priority=RetrievalPriority.NORMAL,
        max_results=max_results,
    )


def _parse_step(raw: dict) -> RetrievalStep | None:
    strategy_value = raw.get("strategy")
    try:
        strategy = RetrievalStrategy(strategy_value)
    except ValueError:
        logger.warning(
            "Planner chose unknown strategy %r - dropping step", strategy_value
        )
        return None

    direction = raw.get("direction")
    if direction is not None and direction not in _DIRECTIONS:
        direction = None

    return RetrievalStep(
        strategy=strategy,
        target=raw.get("target"),
        query=raw.get("query"),
        direction=direction,
    )
