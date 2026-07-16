import contextvars
import logging

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    return _request_id_var.get()


def set_request_id(value: str) -> contextvars.Token:
    return _request_id_var.set(value)


def reset_request_id(token: contextvars.Token) -> None:
    _request_id_var.reset(token)


class RequestIdLogFilter(logging.Filter):
    """Injects the current request's id into every log record emitted while
    handling it - not distributed tracing, just enough to grep one request's
    log lines out of an interleaved, concurrent server log. Works for log
    calls anywhere in the codebase (services, retrieval, reasoning, ...)
    without any of those modules knowing about request ids, since it reads
    from a contextvar rather than needing the id threaded through every call.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True
