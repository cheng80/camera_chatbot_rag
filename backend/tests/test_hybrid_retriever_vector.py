from pathlib import Path

from backend.app.indexing.fts_index import build_fts_index
from backend.app.schemas.search import SearchRequest
from backend.app.services.hybrid_retriever import HybridRetriever, HybridRetrieverConfig
from backend.app.services.vector_search import (
    VectorSearchAdapter,
    VectorSearchRequest,
    VectorSearchResult,
)
from backend.tests.hybrid_retriever_fixtures import (
    hybrid_chunk,
    write_hybrid_source_validation_fixture,
)


class FakeVectorSearchAdapter:
    def search(self, request: VectorSearchRequest) -> tuple[VectorSearchResult, ...]:
        assert request.query == "제브라"
        return (
            VectorSearchResult(
                chunk_id="sample_manual:vector:12:1",
                document_id="sample_manual",
                model_ids=("DC-G9M2",),
                page_start=12,
                page_end=12,
                section_title="촬영 보조",
                content="제브라 패턴은 노출 확인에 사용하는 촬영 보조 기능입니다.",
                score=0.75,
            ),
        )


class MultiModelVectorSearchAdapter:
    def search(self, request: VectorSearchRequest) -> tuple[VectorSearchResult, ...]:
        _ = request
        return (
            VectorSearchResult(
                chunk_id="sample_manual:vector:12:multi",
                document_id="sample_manual",
                model_ids=("DC-TZ99", "DC-ZS99"),
                page_start=12,
                page_end=12,
                section_title="촬영 보조",
                content="제브라 패턴은 노출 확인에 사용하는 촬영 보조 기능입니다.",
                score=0.75,
            ),
        )


class UniqueVectorSearchAdapter:
    def search(self, request: VectorSearchRequest) -> tuple[VectorSearchResult, ...]:
        assert request.query == "제브라"
        return (
            VectorSearchResult(
                chunk_id="sample_manual:vector:13:1",
                document_id="sample_manual",
                model_ids=("DC-G9M2",),
                page_start=13,
                page_end=13,
                section_title="촬영 보조 추가",
                content="제브라 표시 강도는 촬영 보조 메뉴에서 조정합니다.",
                score=0.7,
            ),
        )


class InvalidVectorSearchAdapter:
    def search(self, request: VectorSearchRequest) -> tuple[VectorSearchResult, ...]:
        _ = request
        return (
            VectorSearchResult(
                chunk_id="missing_manual:vector:99:1",
                document_id="missing_manual",
                model_ids=("DC-G9M2",),
                page_start=99,
                page_end=99,
                section_title="촬영 보조",
                content="제브라 패턴",
                score=0.5,
            ),
        )


def test_hybrid_retriever_can_use_vector_adapter_when_fts_has_no_results(
    tmp_path: Path,
) -> None:
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(tmp_path=tmp_path)
    retriever = _retriever(
        index_path=tmp_path / "missing.sqlite3",
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        vector_adapter=FakeVectorSearchAdapter(),
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "ok"
    assert response.cards[0].feature_id == "sample_manual:vector:12:1"
    assert response.cards[0].confidence == 0.75


def test_hybrid_retriever_merges_fts_and_vector_results(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        hybrid_chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(
        tmp_path=tmp_path,
        pages=(12, 13),
    )
    retriever = _retriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        vector_adapter=UniqueVectorSearchAdapter(),
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "ok"
    assert tuple(source.page for card in response.cards for source in card.sources) == (
        12,
        13,
    )


def test_hybrid_retriever_caps_fused_results_to_top_k(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        hybrid_chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(
        tmp_path=tmp_path,
        pages=(12, 13),
    )
    retriever = _retriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        vector_adapter=UniqueVectorSearchAdapter(),
    )

    response = retriever.search(
        SearchRequest(query="제브라", model_ids=["DC-G9M2"], top_k=1),
    )

    assert response.retrieval_status == "ok"
    assert len(response.cards) == 1


def test_hybrid_retriever_deduplicates_fts_and_vector_source_page(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        hybrid_chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(tmp_path=tmp_path)
    retriever = _retriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        vector_adapter=FakeVectorSearchAdapter(),
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "ok"
    assert len(response.cards) == 1
    assert response.cards[0].sources[0].page == 12


def test_hybrid_retriever_uses_requested_model_for_vector_source(
    tmp_path: Path,
) -> None:
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(tmp_path=tmp_path)
    retriever = _retriever(
        index_path=tmp_path / "missing.sqlite3",
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        vector_adapter=MultiModelVectorSearchAdapter(),
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-ZS99"]))

    assert response.retrieval_status == "ok"
    assert response.cards[0].sources[0].model_id == "DC-ZS99"


def test_hybrid_retriever_reports_insufficient_evidence_for_invalid_vector_source(
    tmp_path: Path,
) -> None:
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(tmp_path=tmp_path)
    retriever = _retriever(
        index_path=tmp_path / "missing.sqlite3",
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        vector_adapter=InvalidVectorSearchAdapter(),
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "insufficient_evidence"
    assert response.cards == []


def _retriever(
    *,
    index_path: Path,
    registry_dir: Path,
    pages_dir: Path,
    vector_adapter: VectorSearchAdapter,
) -> HybridRetriever:
    return HybridRetriever(
        config=HybridRetrieverConfig(
            index_path=index_path,
            registry_dir=registry_dir,
            pages_dir=pages_dir,
            vector_adapter=vector_adapter,
        ),
    )
