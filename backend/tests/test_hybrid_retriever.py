from pathlib import Path

from backend.app.indexing.fts_index import build_fts_index
from backend.app.schemas.search import SearchRequest
from backend.app.services.hybrid_retriever import HybridRetriever
from backend.app.services.vector_search import (
    VectorSearchRequest,
    VectorSearchResult,
)
from backend.tests.hybrid_retriever_fixtures import (
    hybrid_chunk,
    hybrid_model,
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


def test_hybrid_retriever_returns_feature_cards_from_fts_index(
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
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "ok"
    assert response.cards[0].evidence_status == "source_validated"
    assert response.cards[0].feature_name == "촬영 보조"
    assert response.cards[0].sources[0].document_id == "sample_manual"
    assert response.cards[0].sources[0].page == 12
    assert response.cards[0].supported_models[0].model_id == "DC-G9M2"
    assert (
        response.cards[0].sources[0].viewer_url == "/api/viewer/sample_manual/pages/12"
    )


def test_hybrid_retriever_reports_not_indexed_when_index_missing(
    tmp_path: Path,
) -> None:
    retriever = HybridRetriever(index_path=tmp_path / "missing.sqlite3")

    response = retriever.search(SearchRequest(query="제브라"))

    assert response.retrieval_status == "not_indexed"
    assert response.cards == []


def test_hybrid_retriever_can_use_vector_adapter_when_fts_has_no_results(
    tmp_path: Path,
) -> None:
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(tmp_path=tmp_path)
    retriever = HybridRetriever(
        index_path=tmp_path / "missing.sqlite3",
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        vector_adapter=FakeVectorSearchAdapter(),
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "ok"
    assert response.cards[0].feature_id == "sample_manual:vector:12:1"
    assert response.cards[0].confidence == 0.75


def test_hybrid_retriever_uses_requested_model_for_vector_source(
    tmp_path: Path,
) -> None:
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(tmp_path=tmp_path)
    retriever = HybridRetriever(
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
    retriever = HybridRetriever(
        index_path=tmp_path / "missing.sqlite3",
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        vector_adapter=InvalidVectorSearchAdapter(),
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "insufficient_evidence"
    assert response.cards == []


def test_hybrid_retriever_uses_requested_model_for_multi_model_source(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        hybrid_chunk(model_ids=("DC-TZ99", "DC-ZS99")).model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(tmp_path=tmp_path)
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-ZS99"]))

    assert response.retrieval_status == "ok"
    assert response.cards[0].sources[0].model_id == "DC-ZS99"


def test_hybrid_retriever_detects_model_name_in_query(
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
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        models=(hybrid_model("DC-G9M2", "LUMIX G9II"),),
    )

    response = retriever.search(SearchRequest(query="G9M2 제브라 패턴"))

    assert response.retrieval_status == "ok"
    assert response.normalized_query.detected_model_ids == ["DC-G9M2"]
    assert response.normalized_query.search_query == "제브라 패턴"
    assert response.cards[0].sources[0].model_id == "DC-G9M2"


def test_hybrid_retriever_handles_natural_language_setting_query(
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
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        models=(hybrid_model("DC-G9M2", "LUMIX G9II"),),
    )

    response = retriever.search(
        SearchRequest(query="G9M2에서 제브라 패턴 어디서 설정해?"),
    )

    assert response.retrieval_status == "ok"
    assert response.normalized_query.search_query == "제브라 패턴"
    assert response.cards[0].sources[0].model_id == "DC-G9M2"


def test_hybrid_retriever_drops_unvalidated_source_cards(
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
        pages=(99,),
    )
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "insufficient_evidence"
    assert response.cards == []


def test_hybrid_retriever_deduplicates_same_source_page(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    duplicated = (
        hybrid_chunk(chunk_id="sample_manual:opendl:12:1").model_dump_json(),
        hybrid_chunk(chunk_id="sample_manual:opendl:12:2").model_dump_json(),
    )
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        "\n".join(duplicated) + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(tmp_path=tmp_path)
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "ok"
    assert len(response.cards) == 1
