import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from codebase_agent import __version__
from codebase_agent.api.logging_config import configure_api_logging
from codebase_agent.api.middleware import RequestIdMiddleware
from codebase_agent.api.request_context import get_request_id
from codebase_agent.api.routes import (
    insights_router,
    questions_router,
    repositories_router,
)
from codebase_agent.api.schemas import HealthResponse
from codebase_agent.application.errors import (
    ApplicationError,
    IngestionFailedError,
    RepositoryIncompatibleError,
    RepositoryNotFoundError,
)
from codebase_agent.config import settings
from codebase_agent.embeddings import CodeEmbedder
from codebase_agent.insights import AnalysisRunner
from codebase_agent.knowledge import KnowledgeBaseRegistry
from codebase_agent.llm import GroqClient
from codebase_agent.reasoning import ReasoningEngine
from codebase_agent.retrieval.executor import RetrievalExecutor
from codebase_agent.retrieval.planner import RetrievalPlanner
from codebase_agent.storage import CodeVectorStore

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR = {
    RepositoryNotFoundError: 404,
    RepositoryIncompatibleError: 409,
    IngestionFailedError: 422,
}


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Expensive, long-lived resources: constructed once here, not per
    # request - see dependencies.py. KnowledgeBaseRegistry in particular
    # caches a KnowledgeBase per repo, so rebuilding it per request would
    # defeat its entire purpose.
    app.state.embedder = CodeEmbedder()
    app.state.vector_store = CodeVectorStore()
    app.state.kb_registry = KnowledgeBaseRegistry()
    app.state.planner = RetrievalPlanner(llm=GroqClient())
    app.state.executor = RetrievalExecutor()
    app.state.reasoning_engine = ReasoningEngine(llm=GroqClient())
    app.state.analysis_runner = AnalysisRunner()
    logger.info("codebase-agent API started (version=%s)", __version__)
    yield


def create_app() -> FastAPI:
    configure_api_logging()

    app = FastAPI(
        title="Codebase Understanding Agent",
        version=__version__,
        lifespan=_lifespan,
    )
    app.add_middleware(RequestIdMiddleware)

    for error_type, http_status in _STATUS_BY_ERROR.items():
        app.add_exception_handler(error_type, _application_error_handler)
    app.add_exception_handler(ApplicationError, _application_error_handler)

    app.include_router(repositories_router)
    app.include_router(questions_router)
    app.include_router(insights_router)

    @app.get("/v1/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(model=settings.groq_model)

    return app


async def _application_error_handler(
    request: Request, exc: ApplicationError
) -> JSONResponse:
    http_status = _STATUS_BY_ERROR.get(type(exc), 500)
    logger.warning("%s: %s", type(exc).__name__, exc)
    return JSONResponse(
        status_code=http_status,
        content={
            "error": type(exc).__name__,
            "message": str(exc),
            "request_id": get_request_id(),
        },
    )


app = create_app()
