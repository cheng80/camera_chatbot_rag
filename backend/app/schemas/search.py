from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.feature_card import FeatureCard


class NormalizedQuery(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    intent: str
    terms: list[str]
    detected_model_ids: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    query: str
    model_ids: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    top_k: int = Field(default=8, ge=1, le=20)
    include_pdf_sources: bool = True
    response_format: str = "feature_cards"


class SearchResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    query: str
    normalized_query: NormalizedQuery
    cards: list[FeatureCard]
    retrieval_status: str
