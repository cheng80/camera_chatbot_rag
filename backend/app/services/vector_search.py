import math
import re
from collections import Counter
from collections.abc import Sequence
from typing import ClassVar, Final, Protocol

from pydantic import BaseModel, ConfigDict, Field

from backend.app.indexing.chunker import ExtractedChunk

TOKEN_PATTERN: Final = re.compile(r"[A-Za-z0-9가-힣]+")
type SparseVector = Counter[str]


class VectorSearchRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=1)
    top_k: int = Field(default=8, ge=1, le=1000)
    model_ids: tuple[str, ...] = Field(default_factory=tuple)


class VectorSearchResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    document_id: str
    model_ids: tuple[str, ...] = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str | None
    content: str
    score: float = Field(ge=0)


class VectorSearchAdapter(Protocol):
    def search(
        self, request: VectorSearchRequest
    ) -> tuple[VectorSearchResult, ...]: ...


class VectorSearchEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    chunk: ExtractedChunk
    vector: dict[str, int]
    norm: float = Field(ge=0)


class InMemoryHashVectorSearchAdapter:
    def __init__(self, *, entries: tuple[VectorSearchEntry, ...]) -> None:
        self._entries: tuple[VectorSearchEntry, ...] = entries

    @classmethod
    def from_chunks(
        cls,
        *,
        chunks: Sequence[ExtractedChunk],
    ) -> "InMemoryHashVectorSearchAdapter":
        return cls(
            entries=tuple(
                VectorSearchEntry(
                    chunk=chunk,
                    vector=dict(vector),
                    norm=_norm(vector),
                )
                for chunk in chunks
                for vector in (_to_sparse_vector(chunk.content),)
            ),
        )

    def search(self, request: VectorSearchRequest) -> tuple[VectorSearchResult, ...]:
        query_vector = _to_sparse_vector(request.query)
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
            for entry in self._entries
            if _matches_model_filter(
                model_ids=entry.chunk.model_ids,
                requested_model_ids=request.model_ids,
            )
        )
        ranked = sorted(scored, key=lambda result: result.score, reverse=True)
        return tuple(result for result in ranked if result.score > 0)[: request.top_k]


def _result_from_entry(
    *,
    entry: VectorSearchEntry,
    score: float,
) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=entry.chunk.chunk_id,
        document_id=entry.chunk.document_id,
        model_ids=entry.chunk.model_ids,
        page_start=entry.chunk.page_start,
        page_end=entry.chunk.page_end,
        section_title=entry.chunk.section_title,
        content=entry.chunk.content,
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
    requested_model_ids: tuple[str, ...],
) -> bool:
    return not requested_model_ids or bool(
        set(model_ids).intersection(requested_model_ids),
    )
