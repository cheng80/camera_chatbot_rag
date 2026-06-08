from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.search import SearchRequest, SearchResponse


class SearchExpandRequest(SearchRequest):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    max_expanded_queries: int = Field(default=6, ge=1, le=12)


class SearchExpandResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    status: Literal["ok", "unavailable"]
    notice: str
    expanded_queries: list[str]
    response: SearchResponse
