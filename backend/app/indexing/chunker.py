from collections.abc import Sequence
from hashlib import sha256
from typing import ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.indexing.pdf_extractor import ExtractedPage

ChunkType = Literal[
    "caption",
    "heading",
    "image",
    "list",
    "page",
    "paragraph",
    "table",
    "text_block",
]


class ExtractedChunk(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    model_ids: tuple[str, ...] = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str | None = None
    chunk_type: ChunkType
    content: str = Field(min_length=1)
    char_count: int = Field(ge=1)
    source_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def page_end_must_not_precede_start(self) -> Self:
        if self.page_end < self.page_start:
            msg = "page_end must be greater than or equal to page_start"
            raise ValueError(msg)
        return self


def build_page_chunks(pages: Sequence[ExtractedPage]) -> tuple[ExtractedChunk, ...]:
    return tuple(
        ExtractedChunk(
            chunk_id=f"{page.document_id}:page:{page.page}",
            document_id=page.document_id,
            model_ids=page.model_ids,
            page_start=page.page,
            page_end=page.page,
            section_title=None,
            chunk_type="page",
            content=page.text,
            char_count=page.char_count,
            source_hash=content_hash(page.text),
        )
        for page in pages
        if page.text
    )


def content_hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()
