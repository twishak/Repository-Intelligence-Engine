import json
import logging

from codebase_agent.graph.state import AgentState
from codebase_agent.llm import GroqClient

logger = logging.getLogger(__name__)

_STRATEGIES = ("semantic_search", "find_by_qualified_name", "find_references")

_ROUTER_TOOL = {
    "type": "function",
    "function": {
        "name": "select_retrieval_strategy",
        "description": "Choose how to retrieve code context for the user's question.",
        "parameters": {
            "type": "object",
            "properties": {
                "strategy": {
                    "type": "string",
                    "enum": list(_STRATEGIES),
                    "description": (
                        "'semantic_search' for open-ended/conceptual questions (e.g. 'where is "
                        "X handled'); 'find_by_qualified_name' when the exact symbol is already "
                        "named (e.g. 'explain what X does'); 'find_references' for 'what would "
                        "break if I changed Y' questions."
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": (
                        "The exact function/method/class name or dotted qualified name to look "
                        "up. Required for 'find_by_qualified_name' and 'find_references', omit "
                        "for 'semantic_search'."
                    ),
                },
            },
            "required": ["strategy"],
        },
    },
}

_SYSTEM_PROMPT = (
    "You route questions about a codebase to the best retrieval strategy. "
    "Call select_retrieval_strategy exactly once."
)


def route_question(llm: GroqClient, state: AgentState) -> dict:
    message = llm.chat(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": state["question"]},
        ],
        tools=[_ROUTER_TOOL],
        tool_choice={
            "type": "function",
            "function": {"name": "select_retrieval_strategy"},
        },
    )
    strategy, symbol = _parse_routing_decision(message)
    return {"retrieval_strategy": strategy, "target_symbol": symbol}


def _parse_routing_decision(message) -> tuple[str, str | None]:
    tool_calls = message.tool_calls or []
    if not tool_calls:
        logger.warning("Router returned no tool call - defaulting to semantic_search")
        return "semantic_search", None

    try:
        arguments = json.loads(tool_calls[0].function.arguments)
        strategy = arguments["strategy"]
        symbol = arguments.get("symbol")
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(
            "Router response malformed (%s) - defaulting to semantic_search", e
        )
        return "semantic_search", None

    if strategy not in _STRATEGIES:
        logger.warning(
            "Router chose unknown strategy %r - defaulting to semantic_search", strategy
        )
        return "semantic_search", None

    # Exact-match strategies are useless without a symbol to look up.
    if strategy in ("find_by_qualified_name", "find_references") and not symbol:
        logger.warning(
            "Router chose %s without a symbol - defaulting to semantic_search", strategy
        )
        return "semantic_search", None

    return strategy, symbol
