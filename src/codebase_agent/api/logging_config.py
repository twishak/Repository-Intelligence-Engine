import logging

from codebase_agent.api.request_context import RequestIdLogFilter

_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"


def configure_api_logging(level: int = logging.INFO) -> None:
    """Plain (non-Rich) logging for the API process - server logs are read by
    tooling/log aggregation, not a human terminal, unlike the CLI/scripts.
    Every record gets the current request's id via RequestIdLogFilter.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler.addFilter(RequestIdLogFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
