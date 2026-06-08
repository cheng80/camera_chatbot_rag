from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_aliases(name: str) -> AliasChoices:
    return AliasChoices(f"CAMERA_{name}", f"LUMIX_{name}")


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_prefix="CAMERA_",
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    app_name: str = Field(
        default="Camera Manual Assistant",
        validation_alias=_env_aliases("APP_NAME"),
    )
    active_brand_id: str = Field(
        default="panasonic_lumix",
        validation_alias=_env_aliases("ACTIVE_BRAND_ID"),
    )
    brands_config_path: Path = Field(
        default=Path("configs/brands.json"),
        validation_alias=_env_aliases("BRANDS_CONFIG_PATH"),
    )
    brand_name: str = Field(
        default="Panasonic LUMIX",
        validation_alias=_env_aliases("BRAND_NAME"),
    )
    brand_mark: str = Field(default="PL", validation_alias=_env_aliases("BRAND_MARK"))
    debug: bool = Field(default=False, validation_alias=_env_aliases("DEBUG"))
    static_dir: Path = Field(
        default=Path("web"),
        validation_alias=_env_aliases("STATIC_DIR"),
    )
    data_dir: Path = Field(
        default=Path("data"),
        validation_alias=_env_aliases("DATA_DIR"),
    )
    allowed_origins: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices(
            "CAMERA_ALLOWED_ORIGINS",
            "LUMIX_ALLOWED_ORIGINS",
            "CORS_ORIGINS",
        ),
    )
    enable_local_vector: bool = Field(
        default=False,
        validation_alias=_env_aliases("ENABLE_LOCAL_VECTOR"),
    )
    llm_base_url: str = Field(
        default="http://127.0.0.1:11434/v1",
        validation_alias=_env_aliases("LLM_BASE_URL"),
    )
    llm_api_key: str = Field(
        default="local",
        validation_alias=_env_aliases("LLM_API_KEY"),
    )
    llm_selection_mode: Literal["fixed", "auto"] = Field(
        default="auto",
        validation_alias=_env_aliases("LLM_SELECTION_MODE"),
    )
    llm_model: str = Field(
        default="hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        validation_alias=_env_aliases("LLM_MODEL"),
    )
    llm_fast_model: str = Field(
        default="hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        validation_alias=_env_aliases("LLM_FAST_MODEL"),
    )
    llm_thinking_model: str = Field(
        default="hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
        validation_alias=_env_aliases("LLM_THINKING_MODEL"),
    )
    llm_comparison_models: list[str] = Field(
        default_factory=lambda: [
            "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        ],
        validation_alias=_env_aliases("LLM_COMPARISON_MODELS"),
    )
    llm_rewrite_enabled: bool = Field(
        default=True,
        validation_alias=_env_aliases("LLM_REWRITE_ENABLED"),
    )
    llm_rewrite_on_search_enabled: bool = Field(
        default=False,
        validation_alias=_env_aliases("LLM_REWRITE_ON_SEARCH_ENABLED"),
    )
    llm_rewrite_model: str = Field(
        default="hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        validation_alias=_env_aliases("LLM_REWRITE_MODEL"),
    )
    llm_rewrite_fallback_models: list[str] = Field(
        default_factory=lambda: [
            "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        ],
        validation_alias=_env_aliases("LLM_REWRITE_FALLBACK_MODELS"),
    )
    llm_rewrite_max_tokens: int = Field(
        default=128,
        ge=1,
        validation_alias=_env_aliases("LLM_REWRITE_MAX_TOKENS"),
    )
    llm_rewrite_think: bool = Field(
        default=False,
        validation_alias=_env_aliases("LLM_REWRITE_THINK"),
    )
    llm_rewrite_warmup_enabled: bool = Field(
        default=False,
        validation_alias=_env_aliases("LLM_REWRITE_WARMUP_ENABLED"),
    )
    llm_query_expansion_enabled: bool = Field(
        default=True,
        validation_alias=_env_aliases("LLM_QUERY_EXPANSION_ENABLED"),
    )
    llm_query_expansion_model: str = Field(
        default="hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        validation_alias=_env_aliases("LLM_QUERY_EXPANSION_MODEL"),
    )
    llm_query_expansion_fallback_models: list[str] = Field(
        default_factory=lambda: [
            "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        ],
        validation_alias=_env_aliases("LLM_QUERY_EXPANSION_FALLBACK_MODELS"),
    )
    llm_query_expansion_max_tokens: int = Field(
        default=160,
        ge=1,
        validation_alias=_env_aliases("LLM_QUERY_EXPANSION_MAX_TOKENS"),
    )
    llm_query_expansion_think: bool = Field(
        default=False,
        validation_alias=_env_aliases("LLM_QUERY_EXPANSION_THINK"),
    )
    llm_query_expansion_max_terms: int = Field(
        default=6,
        ge=1,
        le=12,
        validation_alias=_env_aliases("LLM_QUERY_EXPANSION_MAX_TERMS"),
    )
    embedding_base_url: str = Field(
        default="http://127.0.0.1:11434/v1",
        validation_alias=_env_aliases("EMBEDDING_BASE_URL"),
    )
    embedding_api_key: str = Field(
        default="local",
        validation_alias=_env_aliases("EMBEDDING_API_KEY"),
    )
    embedding_model: str = Field(
        default="bge-m3",
        validation_alias=_env_aliases("EMBEDDING_MODEL"),
    )
    llm_request_timeout_seconds: float = Field(
        default=120,
        gt=0,
        validation_alias=_env_aliases("LLM_REQUEST_TIMEOUT_SECONDS"),
    )
    llm_temperature: float = Field(
        default=0.2,
        ge=0,
        le=2,
        validation_alias=_env_aliases("LLM_TEMPERATURE"),
    )
    llm_max_tokens: int = Field(
        default=512,
        ge=1,
        validation_alias=_env_aliases("LLM_MAX_TOKENS"),
    )
    llm_think: bool = Field(
        default=False,
        validation_alias=_env_aliases("LLM_THINK"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
