import re

from codebase_agent.insights.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    make_finding_id,
)
from codebase_agent.intelligence.models import Symbol
from codebase_agent.knowledge import KnowledgeBase

_EXCLUDED_SHORT_NAMES = {"main", "__init__", "__main__"}
_DUNDER = re.compile(r"^__.+__$")


class DeadCodeAnalyzer:
    """Flags symbols with no resolved callers in the static call graph.

    This is inherently heuristic, not sound: Python's dynamism means a
    symbol can be invoked without ever appearing as a resolved call edge
    (framework callbacks, CLI entry points, reflection, pytest test
    discovery). Findings are WARNING severity with an explicit caveat, not
    asserted as fact - see ADR-0004.
    """

    name = "dead_code"

    def analyze(self, kb: KnowledgeBase) -> list[Finding]:
        findings = []
        for symbol in kb.all_symbols():
            if self._is_excluded(symbol):
                continue
            if kb.callers_of(symbol.qualified_name):
                continue
            findings.append(
                Finding(
                    id=make_finding_id(
                        FindingCategory.DEAD_CODE,
                        symbol.qualified_name,
                        str(symbol.start_line),
                    ),
                    category=FindingCategory.DEAD_CODE,
                    severity=FindingSeverity.WARNING,
                    title=f"No callers found for '{symbol.qualified_name}'",
                    description=(
                        f"{symbol.kind} '{symbol.qualified_name}' has no resolved callers in the static "
                        f"call graph. This may be dead code, or it may be invoked dynamically or "
                        f"externally (a CLI entry point, a framework callback, a test discovered by "
                        f"name, an exported public API) - verify before removing."
                    ),
                    qualified_name=symbol.qualified_name,
                    file_path=symbol.file_path,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    details={"kind": symbol.kind},
                )
            )
        return findings

    def _is_excluded(self, symbol: Symbol) -> bool:
        short_name = symbol.qualified_name.rsplit(".", 1)[-1]
        if short_name in _EXCLUDED_SHORT_NAMES or _DUNDER.match(short_name):
            return True
        if short_name.startswith("test_"):
            return True
        path_parts = symbol.file_path.split("/")
        return any(
            part in ("test", "tests") or part.startswith("test_") for part in path_parts
        )
