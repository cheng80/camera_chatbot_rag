from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_prefix="LUMIX_",
        extra="ignore",
        frozen=True,
    )

    app_name: str = "Panasonic LUMIX Manual Assistant"
    debug: bool = False
    static_dir: Path = Path("web")
    data_dir: Path = Path("data")
    allowed_origins: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("LUMIX_ALLOWED_ORIGINS", "CORS_ORIGINS"),
    )
    enable_local_vector: bool = False
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = "local"
    llm_selection_mode: Literal["fixed", "auto"] = "auto"
    llm_model: str = "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M"
    llm_fast_model: str = (
        "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M"
    )
    llm_thinking_model: str = "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M"
    llm_comparison_models: list[str] = Field(
        default_factory=lambda: [
            "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        ],
    )
    llm_rewrite_enabled: bool = True
    llm_rewrite_model: str = "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL"
    llm_rewrite_fallback_models: list[str] = Field(
        default_factory=lambda: [
            "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        ],
    )
    llm_rewrite_max_tokens: int = Field(default=128, ge=1)
    llm_rewrite_think: bool = False
    embedding_base_url: str = "http://127.0.0.1:11434/v1"
    embedding_api_key: str = "local"
    embedding_model: str = "bge-m3"
    llm_request_timeout_seconds: float = Field(default=120, gt=0)
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_max_tokens: int = Field(default=512, ge=1)
    llm_think: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
