import logging

from groq import Groq
from groq.types.chat import ChatCompletionMessage

from codebase_agent.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Thin wrapper around the Groq chat-completions API.

    The underlying SDK client is constructed lazily so importing/instantiating
    this class doesn't require GROQ_API_KEY to be set - useful for tests that
    inject a fake client and never touch the network.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self._model = model or settings.groq_model
        self._api_key = api_key or settings.groq_api_key
        self._client: Groq | None = None

    @property
    def model(self) -> str:
        return self._model

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
    ) -> ChatCompletionMessage:
        client = self._get_client()
        # tools/tool_choice must be omitted entirely rather than passed as an
        # explicit None - the Groq API rejects a literal null for tool_choice.
        kwargs = {"model": self._model, "messages": messages}
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message

    def _get_client(self) -> Groq:
        if self._client is None:
            logger.info("Initializing Groq client for model %s", self._model)
            self._client = Groq(api_key=self._api_key)
        return self._client
