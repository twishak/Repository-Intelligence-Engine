from unittest.mock import Mock

import pytest

from codebase_agent.application.errors import RepositoryNotFoundError
from codebase_agent.application.services.insights_service import InsightsService
from codebase_agent.knowledge import RepoNotIngestedError


def test_analyze_repository_delegates_to_runner():
    runner = Mock()
    report = Mock()
    runner.run.return_value = report
    kb = Mock()
    kb_registry = Mock()
    kb_registry.get.return_value = kb

    service = InsightsService(runner=runner, kb_registry=kb_registry)
    result = service.analyze_repository("repo")

    assert result is report
    runner.run.assert_called_once_with(kb)


def test_raises_repository_not_found():
    kb_registry = Mock()
    kb_registry.get.side_effect = RepoNotIngestedError("repo")

    service = InsightsService(runner=Mock(), kb_registry=kb_registry)

    with pytest.raises(RepositoryNotFoundError):
        service.analyze_repository("repo")
