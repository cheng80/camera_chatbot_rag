from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LUMIX_",
        frozen=True,
    )

    app_name: str = "Panasonic LUMIX Manual Assistant"
    debug: bool = False
    static_dir: Path = Path("web")
    data_dir: Path = Path("data")
    allowed_origins: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    return Settings()
