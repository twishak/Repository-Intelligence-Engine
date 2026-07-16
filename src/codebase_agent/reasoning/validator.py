from codebase_agent.reasoning.result import (
    ReasoningResult,
    ValidationIssue,
    ValidationSeverity,
)
from codebase_agent.retrieval.evidence import EvidenceBundle


class AnswerValidator:
    """Lightweight, deterministic sanity checks between a ReasoningResult
    draft and the EvidenceBundle it was produced from.

    Not a correctness prover - catches obvious inconsistencies (hallucinated
    citation indices, claimed sufficiency with no evidence, an empty answer)
    that are cheap to check without another LLM call. Issues are
    informational only: nothing here triggers a retry or re-prompt, which
    would reintroduce the iteration this feature deliberately avoids.
    """

    def validate(
        self, result: ReasoningResult, evidence_bundle: EvidenceBundle
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues.extend(self._check_citation_indices(result, evidence_bundle))
        issues.extend(self._check_sufficiency_claim(result, evidence_bundle))
        issues.extend(self._check_empty_answer(result))
        issues.extend(self._check_uncited_sufficient_answer(result, evidence_bundle))
        return issues

    def _check_citation_indices(
        self, result: ReasoningResult, evidence_bundle: EvidenceBundle
    ) -> list[ValidationIssue]:
        valid_count = len(evidence_bundle.items)
        return [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Citation [{index}] does not correspond to any retrieved evidence item "
                f"(only {valid_count} available)",
            )
            for index in result.cited_evidence_indices
            if not (1 <= index <= valid_count)
        ]

    def _check_sufficiency_claim(
        self, result: ReasoningResult, evidence_bundle: EvidenceBundle
    ) -> list[ValidationIssue]:
        if result.evidence_sufficient and evidence_bundle.is_empty():
            return [
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Answer claims evidence was sufficient, but no evidence was retrieved",
                )
            ]
        return []

    def _check_empty_answer(self, result: ReasoningResult) -> list[ValidationIssue]:
        if not result.answer.strip():
            return [
                ValidationIssue(
                    severity=ValidationSeverity.ERROR, message="Answer text is empty"
                )
            ]
        return []

    def _check_uncited_sufficient_answer(
        self, result: ReasoningResult, evidence_bundle: EvidenceBundle
    ) -> list[ValidationIssue]:
        if (
            result.evidence_sufficient
            and not evidence_bundle.is_empty()
            and not result.cited_evidence_indices
        ):
            return [
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Answer claims evidence was sufficient but cites no evidence items",
                )
            ]
        return []
