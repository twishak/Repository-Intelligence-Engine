import pytest

from codebase_agent.llm import GroqClient


class _FakeCompletions:
    def __init__(self, message):
        self._message = message
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        return _FakeResponse(self._message)


class _FakeResponse:
    def __init__(self, message):
        self.choices = [_FakeChoice(message)]


class _FakeChoice:
    def __init__(self, message):
        self.message = message


class _FakeChat:
    def __init__(self, message):
        self.completions = _FakeCompletions(message)


class _FakeGroqSDKClient:
    def __init__(self, message):
        self.chat = _FakeChat(message)


def test_chat_returns_the_response_message_and_forwards_arguments():
    fake_message = object()
    client = GroqClient(model="test-model", api_key="fake")
    client._client = _FakeGroqSDKClient(fake_message)  # bypass lazy real-SDK init

    result = client.chat(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "x"}}],
        tool_choice="auto",
    )

    assert result is fake_message
    sent = client._client.chat.completions.last_call_kwargs
    assert sent["model"] == "test-model"
    assert sent["messages"] == [{"role": "user", "content": "hi"}]
    assert sent["tool_choice"] == "auto"


def test_chat_omits_tools_and_tool_choice_when_not_given():
    # The Groq API rejects an explicit `tool_choice: null` - these keys must be
    # absent from the request entirely when the caller doesn't pass them.
    client = GroqClient(model="test-model", api_key="fake")
    client._client = _FakeGroqSDKClient(object())

    client.chat(messages=[{"role": "user", "content": "hi"}])

    sent = client._client.chat.completions.last_call_kwargs
    assert "tools" not in sent
    assert "tool_choice" not in sent


@pytest.mark.integration
def test_chat_against_real_groq_api():
    client = GroqClient()
    message = client.chat(
        messages=[{"role": "user", "content": "Say 'ok' and nothing else."}]
    )
    assert message.content
