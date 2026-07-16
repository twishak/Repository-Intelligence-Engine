from typing import TypedDict

from codebase_agent.reasoning.result import ReasoningResult
from codebase_agent.retrieval.evidence import EvidenceBundle
from codebase_agent.retrieval.plan import RetrievalPlan
from codebase_agent.retrieval.planner import RetrievalContext


class ReasoningState(TypedDict):
    repo_name: str
    question: str
    context: RetrievalContext | None
    plan: RetrievalPlan | None
    evidence: EvidenceBundle | None
    result: ReasoningResult | None
