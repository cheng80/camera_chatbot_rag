import pytest
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.services.vector_search import (
    InMemoryHashVectorSearchAdapter,
    VectorSearchRequest,
    VectorSearchResult,
)
from pydantic import ValidationError


def test_in_memory_hash_vector_search_ranks_matching_chunk() -> None:
    adapter = InMemoryHashVectorSearchAdapter.from_chunks(
        chunks=(
            _chunk(
                chunk_id="stabilization",
                content="손떨림 보정 기능은 촬영 중 흔들림을 줄입니다.",
            ),
            _chunk(
                chunk_id="connectivity",
                content="LUMIX Lab 연결은 스마트폰 전송에 사용합니다.",
            ),
        ),
    )

    results = adapter.search(
        VectorSearchRequest(query="손떨림 보정", top_k=2, model_ids=("DC-G9M2",)),
    )

    assert results[0].chunk_id == "stabilization"
    assert len(results) == 1
    assert results[0].score > 0


def test_in_memory_hash_vector_search_filters_models() -> None:
    adapter = InMemoryHashVectorSearchAdapter.from_chunks(
        chunks=(
            _chunk(
                chunk_id="g9m2",
                content="손떨림 보정",
                model_ids=("DC-G9M2",),
            ),
            _chunk(
                chunk_id="s9",
                content="손떨림 보정",
                model_ids=("DC-S9",),
            ),
        ),
    )

    results = adapter.search(
        VectorSearchRequest(query="손떨림 보정", top_k=5, model_ids=("DC-S9",)),
    )

    assert tuple(result.chunk_id for result in results) == ("s9",)


def test_vector_search_result_rejects_empty_model_ids() -> None:
    with pytest.raises(ValidationError):
        _ = VectorSearchResult(
            chunk_id="invalid",
            document_id="sample_manual",
            model_ids=(),
            page_start=1,
            page_end=1,
            section_title="sample",
            content="sample",
            score=0.1,
        )


def _chunk(
    *,
    chunk_id: str,
    content: str,
    model_ids: tuple[str, ...] = ("DC-G9M2",),
) -> ExtractedChunk:
    return ExtractedChunk(
        chunk_id=chunk_id,
        document_id="sample_manual",
        model_ids=model_ids,
        page_start=1,
        page_end=1,
        section_title="sample",
        chunk_type="paragraph",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )
