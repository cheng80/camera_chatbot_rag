from pathlib import Path
from re import fullmatch
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrandRegistryEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    brand_id: str = Field(min_length=1, max_length=64)
    brand_name: str = Field(min_length=1, max_length=120)
    brand_mark: str = Field(min_length=1, max_length=12)
    data_dir: Path
    rules_dir: Path | None = None

    @field_validator("brand_id")
    @classmethod
    def brand_id_must_be_slug(cls, value: str) -> str:
        if fullmatch(r"[a-z0-9_]+", value) is None:
            msg = "brand_id must contain only lowercase letters, numbers, and _"
            raise ValueError(msg)
        return value


class BrandSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    brand_id: str
    brand_name: str
    brand_mark: str


class BrandCatalog(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    active_brand_id: str
    brands: tuple[BrandRegistryEntry, ...]
