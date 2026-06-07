from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class SearchApiSmokeCase(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    model_ids: tuple[str, ...] = Field(default_factory=tuple)
    expected_document_id: str = Field(min_length=1)
    expected_pages: tuple[int, ...] = Field(min_length=1)
    top_k: int = Field(default=5, ge=1)


class SearchApiSmokeResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    status_code: int
    retrieval_status: str
    card_count: int = Field(ge=0)
    schema_valid: bool
    retrieval_ok: bool
    sources_present: bool
    hit_document: bool
    hit_page: bool
    viewer_url_valid: bool
    evidence_valid: bool
    summary_present: bool
    model_filter_valid: bool
    source_model_consistent: bool
    result_pages: tuple[int, ...]
    result_document_ids: tuple[str, ...]


class SearchApiSmokeReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    case_count: int = Field(ge=0)
    pass_count: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)
    retrieval_ok_rate: float = Field(ge=0, le=1)
    source_presence_rate: float = Field(ge=0, le=1)
    document_hit_rate: float = Field(ge=0, le=1)
    page_hit_rate: float = Field(ge=0, le=1)
    viewer_url_rate: float = Field(ge=0, le=1)
    evidence_rate: float = Field(ge=0, le=1)
    summary_rate: float = Field(ge=0, le=1)
    model_filter_rate: float = Field(ge=0, le=1)
    source_model_consistency_rate: float = Field(ge=0, le=1)
    results: tuple[SearchApiSmokeResult, ...]
