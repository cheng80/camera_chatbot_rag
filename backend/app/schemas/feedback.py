from pydantic import BaseModel, ConfigDict


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    feature_id: str
    rating: str
    note: str | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    feature_id: str
