from unittest.mock import Mock

from codebase_agent.knowledge.registry import KnowledgeBaseRegistry


def test_get_caches_the_built_instance():
    factory = Mock()
    kb = Mock()
    factory.build.return_value = kb
    registry = KnowledgeBaseRegistry(factory=factory)

    first = registry.get("myrepo")
    second = registry.get("myrepo")

    assert first is kb
    assert second is kb
    factory.build.assert_called_once_with("myrepo")


def test_invalidate_forces_rebuild_on_next_get():
    factory = Mock()
    factory.build.side_effect = [Mock(), Mock()]
    registry = KnowledgeBaseRegistry(factory=factory)

    first = registry.get("myrepo")
    registry.invalidate("myrepo")
    second = registry.get("myrepo")

    assert first is not second
    assert factory.build.call_count == 2


def test_list_repos_delegates_to_factory():
    factory = Mock()
    factory.list_available_repos.return_value = ["repo-a", "repo-b"]
    registry = KnowledgeBaseRegistry(factory=factory)

    assert registry.list_repos() == ["repo-a", "repo-b"]
