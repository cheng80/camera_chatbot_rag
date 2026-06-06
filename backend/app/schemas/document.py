from pathlib import Path
from re import fullmatch
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CameraModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    model_id: str
    display_name: str
    product_line: str | None = None


class DocumentSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_id: str
    title: str
    model_ids: list[str]
    language: str = "ko"
    filename: str | None = None
    document_type: str | None = None


class PageReference(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_id: str
    page: int
    image_url: str


class CameraModelRegistryEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    model_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    product_line: str = Field(min_length=1)


class ManualDocumentRegistryEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    model_ids: tuple[str, ...] = Field(min_length=1)
    language: Literal["ko"] = "ko"
    document_type: Literal["full_manual", "advanced_manual", "operating_instructions"]

    @field_validator("document_id")
    @classmethod
    def document_id_must_be_slug(cls, value: str) -> str:
        if fullmatch(r"[a-z0-9_]+", value) is None:
            msg = "document_id must contain only lowercase letters, numbers, and _"
            raise ValueError(msg)
        return value

    @field_validator("filename")
    @classmethod
    def filename_must_be_safe_pdf_basename(cls, value: str) -> str:
        path = Path(value)
        if path.name != value or path.is_absolute() or ".." in path.parts:
            msg = "filename must be a safe basename"
            raise ValueError(msg)
        if path.suffix.lower() != ".pdf":
            msg = "filename must be a PDF file"
            raise ValueError(msg)
        return value


class RegistryCatalog(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    documents: tuple[ManualDocumentRegistryEntry, ...]
    models: tuple[CameraModelRegistryEntry, ...]
