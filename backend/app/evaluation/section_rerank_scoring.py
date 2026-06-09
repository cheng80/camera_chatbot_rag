from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field

from backend.app.indexing.fts_index import FtsSearchResult

SECTION_PAGE_BONUS: Final = 0.75
SECTION_DOCUMENT_BONUS: Final = 0.05


class SectionRange(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)


class RankedChunk(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    result: FtsSearchResult
    score: float


def rerank_chunks(
    *,
    chunks: tuple[FtsSearchResult, ...],
    section_ranges: tuple[SectionRange, ...],
) -> tuple[RankedChunk, ...]:
    ranked = tuple(
        RankedChunk(
            result=chunk,
            score=_base_score(rank) + _section_bonus(
                chunk=chunk,
                section_ranges=section_ranges,
            ),
        )
        for rank, chunk in enumerate(chunks, start=1)
    )
    return tuple(sorted(ranked, key=lambda chunk: chunk.score, reverse=True))


def _base_score(rank: int) -> float:
    return 1 / rank


def _section_bonus(
    *,
    chunk: FtsSearchResult,
    section_ranges: tuple[SectionRange, ...],
) -> float:
    best_bonus = 0.0
    for section_range in section_ranges:
        if chunk.document_id != section_range.document_id:
            continue
        if section_range.page_start <= chunk.page_start <= section_range.page_end:
            best_bonus = max(best_bonus, SECTION_PAGE_BONUS)
            continue
        best_bonus = max(best_bonus, SECTION_DOCUMENT_BONUS)
    return best_bonus
