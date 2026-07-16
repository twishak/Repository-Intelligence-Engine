from fastapi import APIRouter, Depends, status

from codebase_agent.api.dependencies import (
    get_ingestion_service,
    get_repository_service,
)
from codebase_agent.api.schemas import (
    IngestRepositoryRequest,
    RepositoryMetadataResponse,
)
from codebase_agent.application.services import IngestionService, RepositoryService

router = APIRouter(prefix="/v1/repositories", tags=["repositories"])


@router.get("", response_model=list[str])
def list_repositories(
    service: RepositoryService = Depends(get_repository_service),
) -> list[str]:
    return service.list_repositories()


@router.post(
    "", response_model=RepositoryMetadataResponse, status_code=status.HTTP_201_CREATED
)
def ingest_repository(
    body: IngestRepositoryRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> RepositoryMetadataResponse:
    metadata = service.ingest_repository(body.source)
    return RepositoryMetadataResponse.from_domain(metadata)


@router.get("/{repo_name}", response_model=RepositoryMetadataResponse)
def get_repository(
    repo_name: str, service: RepositoryService = Depends(get_repository_service)
) -> RepositoryMetadataResponse:
    metadata = service.get_repository(repo_name)
    return RepositoryMetadataResponse.from_domain(metadata)
