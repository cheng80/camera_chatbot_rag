from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

type RagAnswerMode = Literal["card_template", "llm_inference", "retrieval_only"]


class RetrievedSourceForEval(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    section_title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_text: str = Field(min_length=1)


class RagQualityPrompt(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    system_message: str = Field(min_length=1)
    user_message: str = Field(min_length=1)


class RagAnswerSourceRef(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    page: int = Field(ge=1)


class RagModelAnswer(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    answer: str = Field(min_length=1)
    intent_summary: str = Field(min_length=1)
    source_refs: tuple[RagAnswerSourceRef, ...]
    supported_by_sources: bool
    needs_more_context: bool


class RagModelQualityScore(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(min_length=1)
    answer_mode: RagAnswerMode
    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    raw_answer: str
    parsed_answer: RagModelAnswer | None
    retrieved_sources: tuple[RetrievedSourceForEval, ...]
    latency_ms: float = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    output_chars: int = Field(default=0, ge=0)
    json_valid: bool
    json_recoverable: bool = False
    answer_relevance_pass: bool
    korean_intent_pass: bool
    source_citation_pass: bool
    pdf_source_faithfulness_pass: bool
    unsupported_handling_pass: bool
    overall_pass: bool
    error_message: str | None


class RagModelQualitySummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(min_length=1)
    answer_mode: RagAnswerMode
    case_count: int = Field(ge=0)
    json_valid_rate: float = Field(ge=0, le=1)
    json_recoverable_rate: float = Field(default=0, ge=0, le=1)
    avg_latency_ms: float = Field(default=0, ge=0)
    avg_completion_tokens: float = Field(default=0, ge=0)
    avg_total_tokens: float = Field(default=0, ge=0)
    tokens_per_second: float = Field(default=0, ge=0)
    avg_output_chars: float = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    answer_relevance_rate: float = Field(ge=0, le=1)
    korean_intent_rate: float = Field(ge=0, le=1)
    source_citation_rate: float = Field(ge=0, le=1)
    pdf_source_faithfulness_rate: float = Field(ge=0, le=1)
    unsupported_handling_rate: float = Field(ge=0, le=1)
    overall_pass_rate: float = Field(ge=0, le=1)


class RagModelQualityReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    source_path: str = Field(min_length=1)
    model_count: int = Field(ge=0)
    prompt_count: int = Field(ge=0)
    summaries: tuple[RagModelQualitySummary, ...]
    scores: tuple[RagModelQualityScore, ...]
