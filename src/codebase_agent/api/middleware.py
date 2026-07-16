import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from codebase_agent.api.request_context import reset_request_id, set_request_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns each request a unique id, exposes it via X-Request-ID on the
    response, and makes it available to RequestIdLogFilter for the duration
    of the request.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            reset_request_id(token)
        response.headers["X-Request-ID"] = request_id
        return response
