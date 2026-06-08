from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.evaluation.community_query_classifier import CommunityQueryCandidate

type SourceReferenceKey = tuple[str, str, int]
type CommunityTriageBucket = Literal[
    "ok_with_source",
    "model_missing",
    "lens_accessory_noise",
    "low_signal_query",
    "query_too_broad",
    "needs_synonym",
    "no_results",
]

COMMUNITY_CANDIDATES_ADAPTER: TypeAdapter[tuple[CommunityQueryCandidate, ...]] = (
    TypeAdapter(tuple[CommunityQueryCandidate, ...])
)


class CommunityRetrievalArgs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    brand_id: str
    input_path: Path
    output_path: Path
    limit: int = Field(ge=1)


class CommunityRetrievalSource(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    rank: int = Field(ge=1)
    document_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    feature_name: str = Field(min_length=1)
    section_title: str = Field(min_length=1)
    viewer_url: str = Field(min_length=1)
    source_ref_valid: bool


class CommunityQueryRetrievalCandidate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    post_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    category: str = Field(min_length=1)
    model_mentions: tuple[str, ...]
    resolved_model_ids: tuple[str, ...]
    retrieval_status: str = Field(min_length=1)
    normalized_query: str = Field(min_length=1)
    needs_pdf_label: bool
    triage_bucket: CommunityTriageBucket
    triage_reasons: tuple[str, ...]
    weak_label: bool
    not_human_verified: bool
    sources: tuple[CommunityRetrievalSource, ...]
    source_method: str = "community_retrieval_candidate"


RETRIEVAL_CANDIDATES_ADAPTER: TypeAdapter[
    tuple[CommunityQueryRetrievalCandidate, ...]
] = TypeAdapter(tuple[CommunityQueryRetrievalCandidate, ...])
