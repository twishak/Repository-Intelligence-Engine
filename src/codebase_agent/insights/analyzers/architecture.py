from codebase_agent.insights.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    make_finding_id,
)
from codebase_agent.knowledge import KnowledgeBase

_HUB_LIMIT = 10
_HUB_MIN_IMPORTERS = 2


class ArchitectureAnalyzer:
    """Purely structural, deterministic facts about the repo's shape:
    package/file layout, high-fan-in "hub" files, and entry points.

    Deliberately produces facts, not prose - turning this into an "here's
    how the architecture works" explanation is a future, LLM-based feature
    built on top of RepositoryReport, not part of this analyzer.
    """

    name = "architecture"

    def analyze(self, kb: KnowledgeBase) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._package_structure(kb))
        findings.extend(self._hub_files(kb))
        findings.extend(self._entry_points(kb))
        return findings

    def _package_structure(self, kb: KnowledgeBase) -> list[Finding]:
        packages: dict[str, int] = {}
        for file_path in kb.list_files():
            package = file_path.rsplit("/", 1)[0] if "/" in file_path else "(root)"
            packages[package] = packages.get(package, 0) + 1

        return [
            Finding(
                id=make_finding_id(FindingCategory.ARCHITECTURE, "package", package),
                category=FindingCategory.ARCHITECTURE,
                severity=FindingSeverity.INFO,
                title=f"Package '{package}': {count} file(s)",
                description=f"'{package}' contains {count} source file(s).",
                qualified_name=None,
                file_path=None,
                start_line=None,
                end_line=None,
                details={"package": package, "file_count": count},
            )
            for package, count in sorted(packages.items())
        ]

    def _hub_files(self, kb: KnowledgeBase) -> list[Finding]:
        fan_in: dict[str, int] = {}
        for edge in kb.all_import_edges():
            if edge.resolved_file:
                fan_in[edge.resolved_file] = fan_in.get(edge.resolved_file, 0) + 1

        ranked = sorted(fan_in.items(), key=lambda kv: -kv[1])[:_HUB_LIMIT]
        return [
            Finding(
                id=make_finding_id(FindingCategory.ARCHITECTURE, "hub", file_path),
                category=FindingCategory.ARCHITECTURE,
                severity=FindingSeverity.INFO,
                title=f"'{file_path}' is imported by {count} file(s)",
                description=(
                    f"'{file_path}' has high fan-in ({count} importers), suggesting it's a "
                    f"structurally central module."
                ),
                qualified_name=None,
                file_path=file_path,
                start_line=None,
                end_line=None,
                details={"importer_count": count},
            )
            for file_path, count in ranked
            if count >= _HUB_MIN_IMPORTERS
        ]

    def _entry_points(self, kb: KnowledgeBase) -> list[Finding]:
        return [
            Finding(
                id=make_finding_id(
                    FindingCategory.ARCHITECTURE, "entry_point", symbol.qualified_name
                ),
                category=FindingCategory.ARCHITECTURE,
                severity=FindingSeverity.INFO,
                title=f"Entry point: '{symbol.qualified_name}'",
                description=f"'{symbol.qualified_name}' looks like a script entry point.",
                qualified_name=symbol.qualified_name,
                file_path=symbol.file_path,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                details={},
            )
            for symbol in kb.all_symbols()
            if symbol.kind == "function"
            and symbol.qualified_name.rsplit(".", 1)[-1] == "main"
        ]
