from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

type QueryType = Literal[
    "compact_korean",
    "english_keyword",
    "exact_keyword",
    "menu_setting",
    "model_alias",
    "natural_language",
    "semantic_keyword",
    "troubleshooting",
]
type FeatureCategory = Literal[
    "connectivity",
    "display",
    "exposure",
    "focus",
    "general",
    "photo",
    "power",
    "setup",
    "stabilization",
    "video",
]
type Difficulty = Literal["easy", "medium", "hard"]
type SourceMethod = Literal[
    "manual_seed",
    "section_title_weak_label",
    "semantic_keyword_weak_label",
]


class SearchEvalCase(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    model_ids: tuple[str, ...] = Field(default_factory=tuple)
    expected_document_id: str = Field(min_length=1)
    expected_pages: tuple[int, ...] = Field(min_length=1)
    query_type: QueryType
    feature_category: FeatureCategory
    difficulty: Difficulty
    source_method: SourceMethod
    top_k: int = Field(default=5, ge=1)


class SearchEvalResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    query_type: QueryType
    feature_category: FeatureCategory
    difficulty: Difficulty
    source_method: SourceMethod
    hit_document: bool
    hit_page: bool
    top_rank: int | None
    result_count: int = Field(ge=0)
    result_pages: tuple[int, ...]
    result_document_ids: tuple[str, ...]


class SearchEvalGroupScore(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    group_name: str
    case_count: int = Field(ge=0)
    document_hit_count: int = Field(ge=0)
    page_hit_count: int = Field(ge=0)
    document_hit_rate: float = Field(ge=0, le=1)
    page_hit_rate: float = Field(ge=0, le=1)


class SearchEvalReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    case_count: int = Field(ge=0)
    document_hit_count: int = Field(ge=0)
    page_hit_count: int = Field(ge=0)
    document_hit_rate: float = Field(ge=0, le=1)
    page_hit_rate: float = Field(ge=0, le=1)
    by_query_type: tuple[SearchEvalGroupScore, ...] = Field(default_factory=tuple)
    by_feature_category: tuple[SearchEvalGroupScore, ...] = Field(default_factory=tuple)
    by_difficulty: tuple[SearchEvalGroupScore, ...] = Field(default_factory=tuple)
    results: tuple[SearchEvalResult, ...]
