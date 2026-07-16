from codebase_agent.application.services._kb_lookup import get_knowledge_base
from codebase_agent.knowledge import KnowledgeBaseRegistry
from codebase_agent.reasoning import ReasoningEngine, ReasoningResult
from codebase_agent.reasoning.pipeline import build_reasoning_pipeline
from codebase_agent.retrieval.executor import RetrievalExecutor
from codebase_agent.retrieval.planner import RetrievalContext, RetrievalPlanner


class ReasoningService:
    """Answers a question about a repo, grounded in retrieved evidence.

    Wraps the evidence-driven reasoning engine (reasoning.pipeline), not the
    legacy one-shot graph.pipeline - the reasoning engine is the intended
    production path (ADR-0009/0010); the legacy pipeline remains reachable
    via scripts/ask.py for comparison.
    """

    def __init__(
        self,
        planner: RetrievalPlanner | None = None,
        executor: RetrievalExecutor | None = None,
        engine: ReasoningEngine | None = None,
        kb_registry: KnowledgeBaseRegistry | None = None,
    ) -> None:
        self._kb_registry = kb_registry or KnowledgeBaseRegistry()
        self._pipeline = build_reasoning_pipeline(
            planner, executor, engine, self._kb_registry
        )

    def answer_question(
        self,
        repo_name: str,
        question: str,
        active_file: str | None = None,
        active_symbol: str | None = None,
    ) -> ReasoningResult:
        get_knowledge_base(
            self._kb_registry, repo_name
        )  # raises the application-level errors early

        context = None
        if active_file or active_symbol:
            context = RetrievalContext(
                repo_name=repo_name,
                active_file=active_file,
                active_symbol=active_symbol,
            )

        final_state = self._pipeline.invoke(
            {
                "repo_name": repo_name,
                "question": question,
                "context": context,
                "plan": None,
                "evidence": None,
                "result": None,
            }
        )
        return final_state["result"]
