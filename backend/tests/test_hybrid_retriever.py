from pathlib import Path

from backend.app.indexing.fts_index import build_fts_index
from backend.app.schemas.search import SearchRequest
from backend.app.services.hybrid_retriever import HybridRetriever
from backend.tests.hybrid_retriever_fixtures import (
    hybrid_chunk,
    hybrid_model,
    write_hybrid_source_validation_fixture,
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


def test_hybrid_retriever_promotes_menu_reference_page(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    menu_chunk = hybrid_chunk(
        chunk_id="sample_manual:opendl:535:1",
    ).model_copy(
        update={
            "page_start": 535,
            "page_end": 535,
            "section_title": "[기타 (사진)]",
            "content": "• [라이브 뷰 합성]([라이브 뷰 합성]: 253)",
        },
    )
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        menu_chunk.model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(
        tmp_path=tmp_path,
        pages=(253, 535),
    )
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        models=(hybrid_model("DC-G9M2", "LUMIX G9II"),),
    )

    response = retriever.search(
        SearchRequest(query="G9M2 라이브 뷰 합성", model_ids=["DC-G9M2"]),
    )

    assert response.retrieval_status == "ok"
    assert response.cards[0].sources[0].page == 253
    assert response.cards[0].sources[0].section_title == "라이브 뷰 합성"
    assert (
        response.cards[0].sources[0].viewer_url == "/api/viewer/sample_manual/pages/253"
    )


def test_hybrid_retriever_keeps_specific_source_when_reference_label_is_broader(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    proxy_chunk = hybrid_chunk(
        chunk_id="sample_manual:opendl:177:1",
    ).model_copy(
        update={
            "page_start": 177,
            "page_end": 177,
            "section_title": "4 프록시 촬영을 설정하십시오.",
            "content": (
                "프록시 녹화 설정. "
                "(HDMI를 통한 RAW 데이터 출력 시 프록시 녹화: 585)"
            ),
        },
    )
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        proxy_chunk.model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(
        tmp_path=tmp_path,
        pages=(177, 585),
    )
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        models=(hybrid_model("DC-G9M2", "LUMIX G9II"),),
    )

    response = retriever.search(
        SearchRequest(query="프록시 녹화", model_ids=["DC-G9M2"]),
    )

    assert response.retrieval_status == "ok"
    assert response.cards[0].sources[0].page == 177


def test_hybrid_retriever_keeps_source_when_reference_label_has_no_terms(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    spaced_label_chunk = hybrid_chunk(
        chunk_id="sample_manual:opendl:44:1",
    ).model_copy(
        update={
            "page_start": 44,
            "page_end": 44,
            "section_title": "셔터 설정",
            "content": "셔터 설정입니다. ([화 질]: 135)",
        },
    )
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        spaced_label_chunk.model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(
        tmp_path=tmp_path,
        pages=(44, 135),
    )
    retriever = HybridRetriever(
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        models=(hybrid_model("DC-G9M2", "LUMIX G9II"),),
    )

    response = retriever.search(
        SearchRequest(query="셔터 설정", model_ids=["DC-G9M2"]),
    )

    assert response.retrieval_status == "ok"
    assert response.cards[0].sources[0].page == 44


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
