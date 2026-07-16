from pathlib import Path
from string import Template

from codebase_agent.retrieval.evidence import EvidenceItem

# Bump whenever system_prompt.txt or user_prompt.txt changes meaningfully, so
# ReasoningResult.prompt_version lets evaluation/debugging tell which prompt
# version produced a given answer.
PROMPT_VERSION = "v1"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def render_system_prompt() -> str:
    return (_PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")


def render_user_prompt(
    question: str, numbered_evidence: list[tuple[int, EvidenceItem]]
) -> str:
    template = Template((_PROMPTS_DIR / "user_prompt.txt").read_text(encoding="utf-8"))
    return template.substitute(
        question=question, evidence=_format_evidence(numbered_evidence)
    )


def _format_evidence(numbered_evidence: list[tuple[int, EvidenceItem]]) -> str:
    if not numbered_evidence:
        return "(no evidence retrieved)"

    blocks = []
    for index, item in numbered_evidence:
        location = (
            f"{item.file_path}:{item.start_line}-{item.end_line}"
            if item.file_path
            else "(no location)"
        )
        confidence = f"{item.confidence:.2f}" if item.confidence is not None else "n/a"
        blocks.append(
            f"[{index}] source={item.source.value} location={location} confidence={confidence}\n"
            f"reason: {item.explanation}\n"
            f"{item.content}"
        )
    return "\n\n---\n\n".join(blocks)
