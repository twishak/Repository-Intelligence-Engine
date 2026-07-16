import uvicorn

from codebase_agent.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "codebase_agent.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
