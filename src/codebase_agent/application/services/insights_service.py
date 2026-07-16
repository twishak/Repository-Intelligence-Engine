from codebase_agent.application.services._kb_lookup import get_knowledge_base
from codebase_agent.insights import AnalysisRunner, RepositoryReport
from codebase_agent.knowledge import KnowledgeBaseRegistry


class InsightsService:
    """Runs the Repository Insights analyzers over a repo and returns the report."""

    def __init__(
        self,
        runner: AnalysisRunner | None = None,
        kb_registry: KnowledgeBaseRegistry | None = None,
    ) -> None:
        self._runner = runner or AnalysisRunner()
        self._kb_registry = kb_registry or KnowledgeBaseRegistry()

    def analyze_repository(self, repo_name: str) -> RepositoryReport:
        kb = get_knowledge_base(self._kb_registry, repo_name)
        return self._runner.run(kb)
