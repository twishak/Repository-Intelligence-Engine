from typing import TypedDict

from codebase_agent.storage.models import RetrievedChunk


class AgentState(TypedDict):
    repo_name: str
    question: str
    retrieval_strategy: (
        str  # "semantic_search" | "find_by_qualified_name" | "find_references"
    )
    target_symbol: (
        str | None
    )  # extracted identifier; None when strategy is semantic_search
    retrieved_chunks: list[RetrievedChunk]
    answer: str | None
