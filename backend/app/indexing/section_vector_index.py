import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.section_documents import (
    SectionDocument,
    load_section_documents,
)

TOKEN_PATTERN: Final = re.compile(r"[A-Za-z0-9가-힣]+")
SECTION_VECTOR_INDEX_FILENAME: Final = "index.jsonl"
type SparseVector = Counter[str]


class SectionVectorIndexReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_count: int = Field(ge=0)
    section_count: int = Field(ge=0)
    index_path: Path


class SectionVectorIndexEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    section_id: str
    document_id: str
    model_ids: tuple[str, ...] = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str
    content: str
    vector: dict[str, int]
    norm: float = Field(ge=0)


class SectionVectorSearchResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    section_id: str
    document_id: str
    model_ids: tuple[str, ...] = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str
    content: str
    score: float = Field(ge=0)


SECTION_VECTOR_ADAPTER: Final[TypeAdapter[SectionVectorIndexEntry]] = TypeAdapter(
    SectionVectorIndexEntry,
)


def build_section_vector_index(
    *,
    sections_dir: Path,
    index_path: Path,
) -> SectionVectorIndexReport:
    sections = tuple(load_section_documents(sections_dir=sections_dir))
    entries = tuple(_entry_from_section(section) for section in sections)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(entry.model_dump_json() for entry in entries)
    if content:
        content = f"{content}\n"
    _ = index_path.write_text(content, encoding="utf-8")
    load_section_vector_entries.cache_clear()
    return SectionVectorIndexReport(
        document_count=len({entry.document_id for entry in entries}),
        section_count=len(entries),
        index_path=index_path,
    )


def search_section_vector_index(
    *,
    index_path: Path,
    query: str,
    model_ids: Sequence[str] = (),
    top_k: int = 8,
) -> tuple[SectionVectorSearchResult, ...]:
    if not index_path.is_file():
        return ()
    query_vector = _to_sparse_vector(query)
    query_norm = _norm(query_vector)
    scored = tuple(
        _result_from_entry(
            entry=entry,
            score=_cosine_score(
                left=query_vector,
                left_norm=query_norm,
                right=Counter(entry.vector),
                right_norm=entry.norm,
            ),
        )
        for entry in load_section_vector_entries(index_path)
        if _matches_model_filter(
            model_ids=entry.model_ids,
            requested_model_ids=model_ids,
        )
    )
    ranked = sorted(scored, key=lambda result: result.score, reverse=True)
    return tuple(result for result in ranked if result.score > 0)[:top_k]


def _entry_from_section(section: SectionDocument) -> SectionVectorIndexEntry:
    vector = _to_sparse_vector(f"{section.section_title}\n{section.content}")
    return SectionVectorIndexEntry(
        section_id=section.section_id,
        document_id=section.document_id,
        model_ids=section.model_ids,
        page_start=section.page_start,
        page_end=section.page_end,
        section_title=section.section_title,
        content=section.content,
        vector=dict(vector),
        norm=_norm(vector),
    )


@lru_cache(maxsize=4)
def load_section_vector_entries(path: Path) -> tuple[SectionVectorIndexEntry, ...]:
    return tuple(_load_entries(path))


def _load_entries(path: Path) -> Iterable[SectionVectorIndexEntry]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            yield SECTION_VECTOR_ADAPTER.validate_json(line)


def _result_from_entry(
    *,
    entry: SectionVectorIndexEntry,
    score: float,
) -> SectionVectorSearchResult:
    return SectionVectorSearchResult(
        section_id=entry.section_id,
        document_id=entry.document_id,
        model_ids=entry.model_ids,
        page_start=entry.page_start,
        page_end=entry.page_end,
        section_title=entry.section_title,
        content=entry.content,
        score=score,
    )


def _to_sparse_vector(text: str) -> SparseVector:
    return Counter(match.group(0).casefold() for match in TOKEN_PATTERN.finditer(text))


def _norm(vector: SparseVector) -> float:
    return math.sqrt(sum(value * value for value in vector.values()))


def _cosine_score(
    *,
    left: SparseVector,
    left_norm: float,
    right: SparseVector,
    right_norm: float,
) -> float:
    if left_norm == 0 or right_norm == 0:
        return 0
    dot_product = sum(
        left[token] * right[token] for token in left.keys() & right.keys()
    )
    return dot_product / (left_norm * right_norm)


def _matches_model_filter(
    *,
    model_ids: tuple[str, ...],
    requested_model_ids: Sequence[str],
) -> bool:
    return not requested_model_ids or bool(
        set(model_ids).intersection(requested_model_ids),
    )
