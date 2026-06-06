from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class SupportedModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    model_id: str
    support_status: Literal["supported", "unsupported", "unknown"]


class SourceReference(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_id: str
    model_id: str
    page: int
    section_title: str
    viewer_url: str


class FeatureCard(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    feature_id: str
    feature_name: str
    category: str
    summary: str
    supported_models: list[SupportedModel]
    how_to_use: list[str] = Field(default_factory=list)
    menu_path: str | None = None
    cautions: list[str] = Field(default_factory=list)
    sources: list[SourceReference]
    confidence: float
