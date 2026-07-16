import ast
import logging
import textwrap

from codebase_agent.insights.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    make_finding_id,
)
from codebase_agent.knowledge import KnowledgeBase

logger = logging.getLogger(__name__)

_DECISION_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncWith,
    ast.Assert,
    ast.comprehension,
)


class ComplexityAnalyzer:
    """Flags functions/methods above a cyclomatic complexity threshold.

    Re-parses each symbol's persisted source (dedented, since a method's
    sliced text is still indented as it appeared in the file) rather than
    the original file. A snippet that fails to re-parse - a rare edge case,
    e.g. a body containing a column-0 triple-quoted string that defeats
    dedent's assumption - is skipped, not guessed at.
    """

    name = "complexity"

    def __init__(self, threshold: int = 10) -> None:
        self._threshold = threshold

    def analyze(self, kb: KnowledgeBase) -> list[Finding]:
        findings = []
        for symbol in kb.all_symbols():
            if symbol.kind not in ("function", "method"):
                continue
            source = kb.get_source(symbol.qualified_name)
            if not source:
                continue

            complexity = _cyclomatic_complexity(source)
            if complexity is None:
                logger.warning(
                    "Could not re-parse '%s' for complexity analysis - skipping",
                    symbol.qualified_name,
                )
                continue
            if complexity <= self._threshold:
                continue

            findings.append(
                Finding(
                    id=make_finding_id(
                        FindingCategory.COMPLEXITY,
                        symbol.qualified_name,
                        str(symbol.start_line),
                    ),
                    category=FindingCategory.COMPLEXITY,
                    severity=FindingSeverity.WARNING,
                    title=f"High cyclomatic complexity ({complexity}) in '{symbol.qualified_name}'",
                    description=(
                        f"{symbol.kind} '{symbol.qualified_name}' has a cyclomatic complexity of "
                        f"{complexity}, above the threshold of {self._threshold}. Consider splitting it "
                        f"into smaller functions."
                    ),
                    qualified_name=symbol.qualified_name,
                    file_path=symbol.file_path,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    details={
                        "cyclomatic_complexity": complexity,
                        "threshold": self._threshold,
                    },
                )
            )
        return findings


def _cyclomatic_complexity(source: str) -> int | None:
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return None

    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, _DECISION_NODES):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
    return complexity
