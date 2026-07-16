import re

from codebase_agent.insights.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    make_finding_id,
)
from codebase_agent.knowledge import KnowledgeBase

_PATTERN = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b[:\s]*(.*)", re.IGNORECASE)


class TodoAnalyzer:
    """Scans every file's full text for TODO/FIXME/HACK/XXX comment markers.

    Needs whole-file text (not just symbol-bounded slices), since these
    markers commonly appear outside any symbol's body - module headers,
    between functions, in files with no symbols at all.
    """

    name = "todo"

    def analyze(self, kb: KnowledgeBase) -> list[Finding]:
        findings = []
        for file_path in kb.list_files():
            content = kb.get_file_source(file_path)
            if not content:
                continue
            for line_number, line in enumerate(content.splitlines(), start=1):
                match = _PATTERN.search(line)
                if not match:
                    continue
                tag = match.group(1).upper()
                note = match.group(2).strip()
                findings.append(
                    Finding(
                        id=make_finding_id(
                            FindingCategory.TODO, file_path, str(line_number)
                        ),
                        category=FindingCategory.TODO,
                        severity=FindingSeverity.INFO,
                        title=f"{tag} in {file_path}:{line_number}",
                        description=note or f"{tag} comment with no additional detail.",
                        qualified_name=None,
                        file_path=file_path,
                        start_line=line_number,
                        end_line=line_number,
                        details={"tag": tag},
                    )
                )
        return findings
