from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class CardRewriteSource(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1, max_length=160)
    model_id: str = Field(min_length=1, max_length=80)
    page: int = Field(ge=1)
    section_title: str = Field(default="", max_length=300)
    viewer_url: str = Field(min_length=1, max_length=300)


class CardRewriteRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    query: str = Field(min_length=1, max_length=300)
    feature_name: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    sources: list[CardRewriteSource] = Field(min_length=1, max_length=5)


class CardRewriteResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    status: Literal["ok", "unavailable"]
    summary: str
