from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class LocalModelBenchmarkPrompt(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)


class LocalModelBenchmarkCaseResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    ok: bool
    latency_ms: float = Field(ge=0)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    output_chars: int = Field(ge=0)
    error_message: str | None


class LocalModelBenchmarkSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(min_length=1)
    case_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=1)
    avg_latency_ms: float = Field(ge=0)
    median_latency_ms: float = Field(ge=0)
    avg_completion_tokens: float = Field(ge=0)
    tokens_per_second: float = Field(ge=0)
    avg_output_chars: float = Field(ge=0)
    error_count: int = Field(ge=0)


class LocalModelBenchmarkReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    source_path: str = Field(min_length=1)
    model_count: int = Field(ge=0)
    prompt_count: int = Field(ge=0)
    summaries: tuple[LocalModelBenchmarkSummary, ...]
    results: tuple[LocalModelBenchmarkCaseResult, ...]
