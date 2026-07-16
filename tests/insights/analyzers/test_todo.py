from unittest.mock import Mock

from codebase_agent.insights.analyzers.todo import TodoAnalyzer


def test_finds_todo_and_fixme_markers():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py"]
    kb.get_file_source.return_value = (
        "x = 1\n# TODO: refactor this\ny = 2\n# FIXME add validation\n"
    )

    findings = TodoAnalyzer().analyze(kb)

    assert len(findings) == 2
    assert findings[0].details["tag"] == "TODO"
    assert findings[0].start_line == 2
    assert findings[0].description == "refactor this"
    assert findings[1].details["tag"] == "FIXME"


def test_no_markers_produces_no_findings():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py"]
    kb.get_file_source.return_value = "x = 1\ny = 2\n"

    assert TodoAnalyzer().analyze(kb) == []


def test_missing_file_source_is_skipped():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py"]
    kb.get_file_source.return_value = None

    assert TodoAnalyzer().analyze(kb) == []


def test_marker_with_no_note_gets_default_description():
    kb = Mock()
    kb.list_files.return_value = ["pkg/a.py"]
    kb.get_file_source.return_value = "# TODO\n"

    findings = TodoAnalyzer().analyze(kb)

    assert findings[0].description == "TODO comment with no additional detail."
