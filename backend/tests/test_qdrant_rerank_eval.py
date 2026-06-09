from pathlib import Path
from typing import Final

import pytest
from backend.app.evaluation import qdrant_rerank_eval
from backend.app.evaluation.qdrant_rerank_eval import (
    QdrantRerankEvalConfig,
    run_qdrant_rerank_eval_cases,
)
from backend.app.evaluation.qdrant_section_ranges import QdrantSectionRange
from backend.app.evaluation.search_eval_schema import SearchEvalCase
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.fts_index import build_fts_index
from backend.app.services.embedding_client import EmbeddingClientConfig
from backend.app.services.qdrant_vector_store import QdrantConfig

EXPECTED_PAGE: Final = 12


def test_qdrant_expanded_rerank_can_promote_section_page(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        qdrant_rerank_eval,
        "_qdrant_ranges_for_case",
        _fixed_qdrant_ranges,
    )
    report = run_qdrant_rerank_eval_cases(
        cases=(_case(),),
        config=QdrantRerankEvalConfig(
            chunk_index_path=_build_chunk_index(tmp_path),
            qdrant_config=QdrantConfig(
                base_url="http://127.0.0.1:6333",
                collection_name="camera_sections",
                timeout_seconds=5,
            ),
            embedding_config=EmbeddingClientConfig(
                base_url="http://127.0.0.1:9999/v1",
                api_key="test",
                model="bge-m3",
                timeout_seconds=5,
            ),
        ),
    )

    by_strategy = {strategy.strategy: strategy.report for strategy in report.strategies}
    assert tuple(by_strategy) == (
        "chunk_fts",
        "qdrant_section_vector",
        "chunk_qdrant_expanded_rerank",
    )
    assert by_strategy["chunk_fts"].page_hit_rate == 0
    assert by_strategy["qdrant_section_vector"].page_hit_rate == 1
    assert by_strategy["chunk_qdrant_expanded_rerank"].page_hit_rate == 1


def _fixed_qdrant_ranges(
    *,
    case: SearchEvalCase,
    context: qdrant_rerank_eval.QdrantRerankContext,
    top_k: int,
) -> tuple[QdrantSectionRange, ...]:
    _ = (case, context, top_k)
    return (
        QdrantSectionRange(
            document_id="sample",
            page_start=EXPECTED_PAGE,
            page_end=EXPECTED_PAGE,
        ),
    )


def _case() -> SearchEvalCase:
    return SearchEvalCase(
        case_id="focus_peaking",
        query="초점 피킹",
        model_ids=("DC-G9M2",),
        expected_document_id="sample",
        expected_pages=(EXPECTED_PAGE,),
        query_type="exact_keyword",
        feature_category="focus",
        difficulty="easy",
        source_method="manual_seed",
        top_k=1,
    )


def _build_chunk_index(tmp_path: Path) -> Path:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample.jsonl").write_text(
        "\n".join(
            chunk.model_dump_json()
            for chunk in (
                _chunk(page=3, content="초점 피킹 초점 피킹 초점 피킹 일반 안내"),
                _chunk(page=EXPECTED_PAGE, content="초점 피킹 설정 위치"),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    return index_path


def _chunk(*, page: int, content: str) -> ExtractedChunk:
    return ExtractedChunk(
        chunk_id=f"sample:opendl:{page}:1",
        document_id="sample",
        model_ids=("DC-G9M2",),
        page_start=page,
        page_end=page,
        section_title="초점 피킹",
        chunk_type="paragraph",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )
