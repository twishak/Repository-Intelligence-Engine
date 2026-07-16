from codebase_agent.reasoning.prompt_loader import (
    PROMPT_VERSION,
    render_system_prompt,
    render_user_prompt,
)
from codebase_agent.retrieval.evidence import EvidenceItem, EvidenceSource


def _item(content: str = "def foo(): ...") -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.SYMBOL,
        qualified_name="pkg.a.foo",
        file_path="pkg/a.py",
        start_line=1,
        end_line=2,
        content=content,
        explanation="Exact match",
        confidence=1.0,
    )


def test_system_prompt_is_nonempty_and_covers_key_rules():
    prompt = render_system_prompt()

    assert prompt.strip()
    assert "evidence" in prompt.lower()
    assert "conflict" in prompt.lower()
    assert "assumption" in prompt.lower()
    assert "limitation" in prompt.lower()


def test_user_prompt_includes_question_and_numbered_evidence():
    prompt = render_user_prompt("where is foo?", [(1, _item())])

    assert "where is foo?" in prompt
    assert "[1]" in prompt
    assert "def foo(): ..." in prompt


def test_user_prompt_handles_no_evidence():
    prompt = render_user_prompt("q", [])

    assert "no evidence" in prompt.lower()


def test_user_prompt_survives_evidence_containing_braces():
    item = _item(content="def foo(x={1: 2}): return {'ok': True}")

    prompt = render_user_prompt("q", [(1, item)])

    assert "{1: 2}" in prompt
    assert "{'ok': True}" in prompt


def test_prompt_version_is_a_nonempty_string():
    assert isinstance(PROMPT_VERSION, str) and PROMPT_VERSION
