from fastapi import APIRouter, Depends

from codebase_agent.api.dependencies import get_reasoning_service
from codebase_agent.api.schemas import AnswerResponse, AskQuestionRequest
from codebase_agent.application.services import ReasoningService

router = APIRouter(prefix="/v1/repositories", tags=["questions"])


@router.post("/{repo_name}/questions", response_model=AnswerResponse)
def ask_question(
    repo_name: str,
    body: AskQuestionRequest,
    service: ReasoningService = Depends(get_reasoning_service),
) -> AnswerResponse:
    result = service.answer_question(
        repo_name,
        body.question,
        active_file=body.active_file,
        active_symbol=body.active_symbol,
    )
    return AnswerResponse.from_domain(result)
