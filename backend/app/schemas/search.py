from re import fullmatch
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.feature_card import FeatureCard


class NormalizedQuery(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    intent: str
    terms: list[str]
    detected_model_ids: list[str] = Field(default_factory=list)
    search_query: str | None = None


class SearchRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    query: str = Field(min_length=1, max_length=300)
    brand_id: str | None = Field(default=None, max_length=64)
    model_ids: list[str] = Field(default_factory=list, max_length=10)
    categories: list[str] = Field(default_factory=list, max_length=10)
    top_k: int = Field(default=8, ge=1, le=1000)
    include_pdf_sources: bool = True
    response_format: Literal["feature_cards"] = "feature_cards"

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "query must not be blank"
            raise ValueError(msg)
        return stripped

    @field_validator("brand_id")
    @classmethod
    def brand_id_must_be_safe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if fullmatch(r"[a-z0-9_]+", value) is None:
            msg = "brand_id must contain only lowercase letters, numbers, and _"
            raise ValueError(msg)
        return value

    @field_validator("model_ids")
    @classmethod
    def model_ids_must_be_safe(cls, values: list[str]) -> list[str]:
        invalid = tuple(
            value for value in values if fullmatch(r"[A-Z0-9-]{2,32}", value) is None
        )
        if invalid:
            msg = "model_ids must contain only A-Z, 0-9, and -"
            raise ValueError(msg)
        return values


class SearchResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    query: str
    normalized_query: NormalizedQuery
    cards: list[FeatureCard]
    retrieval_status: str
