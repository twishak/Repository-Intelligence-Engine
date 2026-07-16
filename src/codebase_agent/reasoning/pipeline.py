from langgraph.graph import END, StateGraph

from codebase_agent.knowledge import KnowledgeBaseRegistry
from codebase_agent.reasoning.engine import ReasoningEngine
from codebase_agent.reasoning.nodes import execute_retrieval, plan_retrieval, reason
from codebase_agent.reasoning.result import ReasoningResult
from codebase_agent.reasoning.state import ReasoningState
from codebase_agent.retrieval.executor import RetrievalExecutor
from codebase_agent.retrieval.planner import RetrievalContext, RetrievalPlanner


def build_reasoning_pipeline(
    planner: RetrievalPlanner | None = None,
    executor: RetrievalExecutor | None = None,
    engine: ReasoningEngine | None = None,
    kb_registry: KnowledgeBaseRegistry | None = None,
):
    """Deterministic three-node graph: plan_retrieval -> execute_retrieval ->
    reason. No cycles, no conditional edges, no tool-calling loop - LangGraph
    here is purely sequencing, not agentic control flow.
    """
    planner = planner or RetrievalPlanner()
    executor = executor or RetrievalExecutor()
    engine = engine or ReasoningEngine()
    kb_registry = kb_registry or KnowledgeBaseRegistry()

    graph = StateGraph(ReasoningState)
    graph.add_node("plan_retrieval", lambda state: plan_retrieval(planner, state))
    graph.add_node(
        "execute_retrieval",
        lambda state: execute_retrieval(executor, kb_registry, state),
    )
    graph.add_node("reason", lambda state: reason(engine, state))

    graph.set_entry_point("plan_retrieval")
    graph.add_edge("plan_retrieval", "execute_retrieval")
    graph.add_edge("execute_retrieval", "reason")
    graph.add_edge("reason", END)

    return graph.compile()


def answer_question(
    repo_name: str,
    question: str,
    context: RetrievalContext | None = None,
    planner: RetrievalPlanner | None = None,
    executor: RetrievalExecutor | None = None,
    engine: ReasoningEngine | None = None,
    kb_registry: KnowledgeBaseRegistry | None = None,
) -> ReasoningResult:
    """Convenience entry point: run the pipeline once and return the final ReasoningResult."""
    pipeline = build_reasoning_pipeline(planner, executor, engine, kb_registry)
    initial_state: ReasoningState = {
        "repo_name": repo_name,
        "question": question,
        "context": context,
        "plan": None,
        "evidence": None,
        "result": None,
    }
    final_state = pipeline.invoke(initial_state)
    return final_state["result"]
