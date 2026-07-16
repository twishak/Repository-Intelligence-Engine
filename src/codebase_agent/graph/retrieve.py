import logging

from codebase_agent.graph.state import AgentState
from codebase_agent.retrieval import CodeRetriever

logger = logging.getLogger(__name__)


def retrieve(retriever: CodeRetriever, state: AgentState) -> dict:
    repo_name = state["repo_name"]
    strategy = state["retrieval_strategy"]
    symbol = state["target_symbol"]

    if strategy == "find_by_qualified_name":
        chunks = retriever.find_by_qualified_name(repo_name, symbol)
    elif strategy == "find_references":
        chunks = retriever.find_references(repo_name, symbol)
    else:
        chunks = retriever.semantic_search(repo_name, state["question"])

    logger.info("Retrieved %d chunk(s) via %s", len(chunks), strategy)
    return {"retrieved_chunks": chunks}
