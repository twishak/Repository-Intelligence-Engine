import logging

from codebase_agent.knowledge import KnowledgeBaseRegistry
from codebase_agent.reasoning.engine import ReasoningEngine
from codebase_agent.reasoning.state import ReasoningState
from codebase_agent.retrieval.executor import RetrievalExecutor
from codebase_agent.retrieval.planner import RetrievalPlanner

logger = logging.getLogger(__name__)


def plan_retrieval(planner: RetrievalPlanner, state: ReasoningState) -> dict:
    plan = planner.plan(state["question"], context=state.get("context"))
    logger.info(
        "Planned %d retrieval step(s) (intent=%s)", len(plan.steps), plan.intent
    )
    return {"plan": plan}


def execute_retrieval(
    executor: RetrievalExecutor,
    kb_registry: KnowledgeBaseRegistry,
    state: ReasoningState,
) -> dict:
    kb = kb_registry.get(state["repo_name"])
    evidence = executor.execute(kb, state["question"], state["plan"])
    logger.info("Retrieved %d evidence item(s)", len(evidence))
    return {"evidence": evidence}


def reason(engine: ReasoningEngine, state: ReasoningState) -> dict:
    result = engine.reason(state["evidence"])
    return {"result": result}
