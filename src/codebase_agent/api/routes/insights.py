from fastapi import APIRouter, Depends

from codebase_agent.api.dependencies import get_insights_service
from codebase_agent.api.schemas import RepositoryReportResponse
from codebase_agent.application.services import InsightsService

router = APIRouter(prefix="/v1/repositories", tags=["insights"])


@router.get("/{repo_name}/insights", response_model=RepositoryReportResponse)
def analyze_repository(
    repo_name: str, service: InsightsService = Depends(get_insights_service)
) -> RepositoryReportResponse:
    report = service.analyze_repository(repo_name)
    return RepositoryReportResponse.from_domain(report)
