from fastapi import Request

from codebase_agent.application.services import (
    IngestionService,
    InsightsService,
    ReasoningService,
    RepositoryService,
)
from codebase_agent.knowledge import KnowledgeBaseRegistry

# Expensive, long-lived resources (KnowledgeBaseRegistry's per-repo cache,
# the embedding model, the Groq client) live once on app.state, attached at
# startup - see app.py. Services themselves are cheap, stateless wrappers,
# constructed fresh per request from those shared singletons.


def get_kb_registry(request: Request) -> KnowledgeBaseRegistry:
    return request.app.state.kb_registry


def get_ingestion_service(request: Request) -> IngestionService:
    state = request.app.state
    return IngestionService(
        embedder=state.embedder,
        vector_store=state.vector_store,
        kb_registry=state.kb_registry,
    )


def get_reasoning_service(request: Request) -> ReasoningService:
    state = request.app.state
    return ReasoningService(
        planner=state.planner,
        executor=state.executor,
        engine=state.reasoning_engine,
        kb_registry=state.kb_registry,
    )


def get_insights_service(request: Request) -> InsightsService:
    state = request.app.state
    return InsightsService(runner=state.analysis_runner, kb_registry=state.kb_registry)


def get_repository_service(request: Request) -> RepositoryService:
    return RepositoryService(kb_registry=request.app.state.kb_registry)
