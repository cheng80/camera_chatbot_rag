from fastapi import APIRouter

from backend.app.schemas.feedback import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post("", response_model=FeedbackResponse)
async def create_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    return FeedbackResponse(status="accepted", feature_id=payload.feature_id)
