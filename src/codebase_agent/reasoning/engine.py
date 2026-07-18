import json
import logging
import time
from dataclasses import replace

import groq

from codebase_agent.llm import GroqClient
from codebase_agent.reasoning.prompt_loader import (
    PROMPT_VERSION,
    render_system_prompt,
    render_user_prompt,
)
from codebase_agent.reasoning.result import AnswerConfidence, Citation, ReasoningResult
from codebase_agent.reasoning.validator import AnswerValidator
from codebase_agent.retrieval.evidence import EvidenceBundle

logger = logging.getLogger(__name__)

# The tool JSON schema stays in Python, next to the parser that consumes it -
# unlike the prose prompts, a schema/parser mismatch here fails silently or
# throws deep inside JSON parsing, so the two need to change together.
_REASONING_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_reasoning_result",
        "description": "Submit the final answer, grounded strictly in the supplied evidence.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "The answer, citing evidence inline with bracket numbers like [1], [2].",
                },
                "citations": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Bracket numbers of the evidence items actually relied on.",
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Overall confidence in the answer given the evidence.",
                },
                "evidence_sufficient": {
                    "type": "boolean",
                    "description": "Whether the supplied evidence was enough to answer confidently.",
                },
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Inferences the answer relies on that are not directly confirmed by evidence.",
                },
                "limitations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Known gaps or unresolved aspects of the available evidence - e.g. unresolved "
                        "calls, sparse search results, parts of the question no evidence covered."
                    ),
                },
            },
            "required": ["answer", "confidence", "evidence_sufficient"],
        },
    },
}


class ReasoningEngine:
    """Turns an EvidenceBundle into a grounded, citation-aware ReasoningResult.

    One forced tool call, no loop: the LLM receives all evidence up front and
    reasons over it once. Citations are index-based - the model names which
    evidence item(s) it used, and this class resolves those indices back to
    the exact file/line data already in the EvidenceBundle, rather than
    trusting the model to transcribe locations correctly.
    """

    def __init__(
        self, llm: GroqClient | None = None, validator: AnswerValidator | None = None
    ) -> None:
        self._llm = llm or GroqClient()
        self._validator = validator or AnswerValidator()

    def reason(self, evidence_bundle: EvidenceBundle) -> ReasoningResult:
        start = time.perf_counter()
        numbered_evidence = list(enumerate(evidence_bundle.items, start=1))

        message = self._call_llm(
            messages=[
                {"role": "system", "content": render_system_prompt()},
                {
                    "role": "user",
                    "content": render_user_prompt(
                        evidence_bundle.question, numbered_evidence
                    ),
                },
            ],
            tools=[_REASONING_TOOL],
            tool_choice={
                "type": "function",
                "function": {"name": "submit_reasoning_result"},
            },
        )

        if message is None:
            draft = _fallback_result(
                evidence_bundle,
                self._llm.model,
                "The reasoning service was temporarily unavailable.",
            )
        else:
            draft = _parse_reasoning_output(message, evidence_bundle, self._llm.model)

        issues = self._validator.validate(draft, evidence_bundle)
        return replace(
            draft,
            validation_issues=tuple(issues),
            reasoning_time_seconds=time.perf_counter() - start,
        )

    def _call_llm(self, **kwargs):
        # Groq occasionally rejects a tool-call response with a 400 because the
        # model emitted a value that doesn't match the declared JSON schema
        # (e.g. a string where a boolean is expected) - retrying the identical
        # request has been observed to succeed, so one retry is attempted
        # before degrading to a fallback result rather than crashing outright.
        for attempt in range(2):
            try:
                return self._llm.chat(**kwargs)
            except groq.APIError as e:
                logger.warning(
                    "Groq API call failed (attempt %d/2): %s", attempt + 1, e
                )
        return None


def _fallback_result(
    evidence_bundle: EvidenceBundle, model: str, message: str
) -> ReasoningResult:
    return ReasoningResult(
        question=evidence_bundle.question,
        answer=message,
        confidence=AnswerConfidence.LOW,
        evidence_sufficient=False,
        assumptions=(),
        limitations=(),
        citations=(),
        cited_evidence_indices=(),
        validation_issues=(),
        evidence_bundle=evidence_bundle,
        model=model,
        prompt_version=PROMPT_VERSION,
        reasoning_time_seconds=0.0,
    )


def _parse_reasoning_output(
    message, evidence_bundle: EvidenceBundle, model: str
) -> ReasoningResult:
    tool_calls = message.tool_calls or []
    if not tool_calls:
        logger.warning(
            "Reasoning engine returned no tool call - falling back to a non-answer"
        )
        return _fallback_result(
            evidence_bundle, model, "The model did not return a structured answer."
        )

    try:
        arguments = json.loads(tool_calls[0].function.arguments)
        answer = arguments["answer"]
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Reasoning engine response malformed (%s)", e)
        return _fallback_result(
            evidence_bundle, model, "The model returned a malformed response."
        )

    raw_indices = tuple(
        index for index in arguments.get("citations", []) if isinstance(index, int)
    )
    citations = tuple(
        _resolve_citation(index, evidence_bundle)
        for index in raw_indices
        if _in_range(index, evidence_bundle)
    )

    return ReasoningResult(
        question=evidence_bundle.question,
        answer=answer,
        confidence=_parse_confidence(arguments.get("confidence")),
        evidence_sufficient=bool(arguments.get("evidence_sufficient", False)),
        assumptions=tuple(str(a) for a in arguments.get("assumptions", []) if a),
        limitations=tuple(
            str(limitation)
            for limitation in arguments.get("limitations", [])
            if limitation
        ),
        citations=citations,
        cited_evidence_indices=raw_indices,
        validation_issues=(),
        evidence_bundle=evidence_bundle,
        model=model,
        prompt_version=PROMPT_VERSION,
        reasoning_time_seconds=0.0,
    )


def _in_range(index: int, evidence_bundle: EvidenceBundle) -> bool:
    return 1 <= index <= len(evidence_bundle.items)


def _resolve_citation(index: int, evidence_bundle: EvidenceBundle) -> Citation:
    item = evidence_bundle.items[index - 1]
    return Citation(
        evidence_index=index,
        qualified_name=item.qualified_name,
        file_path=item.file_path,
        start_line=item.start_line,
        end_line=item.end_line,
        source=item.source,
    )


def _parse_confidence(value: object) -> AnswerConfidence:
    try:
        return AnswerConfidence(value)
    except ValueError:
        return AnswerConfidence.LOW
