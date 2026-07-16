from dataclasses import dataclass
from enum import Enum

from codebase_agent.retrieval.evidence import EvidenceBundle, EvidenceSource


class AnswerConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Citation:
    """A resolved reference back to the EvidenceBundle - file/line data taken
    directly from the evidence item, not transcribed by the LLM.
    """

    evidence_index: int  # 1-based, matches the bracket number shown to the LLM
    qualified_name: str | None
    file_path: str | None
    start_line: int | None
    end_line: int | None
    source: EvidenceSource


@dataclass(frozen=True)
class ValidationIssue:
    severity: ValidationSeverity
    message: str


@dataclass(frozen=True)
class ReasoningResult:
    question: str
    answer: str
    confidence: AnswerConfidence
    evidence_sufficient: bool
    # Inferences the answer relies on that aren't directly confirmed by evidence.
    assumptions: tuple[str, ...]
    # Known gaps in the evidence itself (not covered by the search, unresolved
    # edges, etc.) - distinct from assumptions, which are about the answer.
    limitations: tuple[str, ...]
    # Resolved, trustworthy citations - safe to render directly in a UI/API response.
    citations: tuple[Citation, ...]
    # Raw evidence indices exactly as the LLM returned them, unfiltered - lets
    # the validator (and a human debugging) see what was hallucinated or
    # dropped, rather than silently losing that signal during parsing.
    cited_evidence_indices: tuple[int, ...]
    validation_issues: tuple[ValidationIssue, ...]
    evidence_bundle: EvidenceBundle
    model: str
    prompt_version: str
    reasoning_time_seconds: float
