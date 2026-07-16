import pytest

from codebase_agent.chunking.models import CodeChunk
from codebase_agent.config import settings
from codebase_agent.interface import cli
from codebase_agent.storage import CodeVectorStore


class _FakeConsole:
    def __init__(self, inputs=None):
        self._inputs = iter(inputs or [])
        self.printed = []

    def print(self, *args, **kwargs):
        self.printed.append(" ".join(str(a) for a in args))

    def input(self, prompt: str = "") -> str:
        try:
            return next(self._inputs)
        except StopIteration:
            raise EOFError from None

    def status(self, *args, **kwargs):
        return _NullContext()


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _chunk(qualified_name: str = "foo") -> CodeChunk:
    return CodeChunk(
        id=f"a.py::function::{qualified_name}",
        file_path="a.py",
        chunk_type="function",
        qualified_name=qualified_name,
        start_line=1,
        end_line=2,
        content=f"def {qualified_name}(): pass",
        docstring=None,
    )


@pytest.fixture(autouse=True)
def _use_tmp_chroma_dir(tmp_path, monkeypatch):
    # cli.py instantiates CodeVectorStore() with no args, so redirect the
    # default persist location rather than plumbing a store through every fn.
    monkeypatch.setattr(settings, "chroma_dir", tmp_path)


def test_ask_once_raises_if_repo_not_ingested():
    with pytest.raises(SystemExit):
        cli.ask_once("missing-repo", "anything?", console=_FakeConsole())


def test_ask_once_prints_and_returns_the_answer(monkeypatch):
    CodeVectorStore().rebuild_repo_collection("test-repo", [_chunk()], [[1.0, 0.0]])
    monkeypatch.setattr(cli, "answer_question", lambda *a, **k: "the answer")

    console = _FakeConsole()
    result = cli.ask_once("test-repo", "what does foo do?", console=console)

    assert result == "the answer"
    assert console.printed == ["the answer"]


def test_run_repl_exits_immediately_on_exit_command(monkeypatch):
    CodeVectorStore().rebuild_repo_collection("test-repo", [_chunk()], [[1.0, 0.0]])
    calls = []
    monkeypatch.setattr(cli, "answer_question", lambda *a, **k: calls.append(1))

    cli.run_repl("test-repo", console=_FakeConsole(inputs=["exit"]))

    assert calls == []


def test_run_repl_answers_questions_until_exit(monkeypatch):
    CodeVectorStore().rebuild_repo_collection("test-repo", [_chunk()], [[1.0, 0.0]])
    monkeypatch.setattr(cli, "answer_question", lambda *a, **k: "the answer")

    console = _FakeConsole(inputs=["what does foo do?", "exit"])
    cli.run_repl("test-repo", console=console)

    assert "the answer" in console.printed


def test_run_repl_stops_cleanly_on_eof():
    CodeVectorStore().rebuild_repo_collection("test-repo", [_chunk()], [[1.0, 0.0]])

    cli.run_repl("test-repo", console=_FakeConsole(inputs=[]))  # must not raise


def test_run_repl_raises_if_repo_not_ingested():
    with pytest.raises(SystemExit):
        cli.run_repl("missing-repo", console=_FakeConsole(inputs=["exit"]))


def test_list_repos_prints_ingested_repo_names():
    CodeVectorStore().rebuild_repo_collection("repo-a", [_chunk()], [[1.0, 0.0]])

    console = _FakeConsole()
    result = cli.list_repos(console=console)

    assert result == ["repo-a"]
    assert "repo-a" in console.printed


def test_list_repos_reports_when_none_ingested():
    console = _FakeConsole()
    result = cli.list_repos(console=console)

    assert result == []
    assert any("no repositories" in p.lower() for p in console.printed)
