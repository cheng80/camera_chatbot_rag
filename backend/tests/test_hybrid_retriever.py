from pathlib import Path

from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.fts_index import build_fts_index
from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.schemas.search import SearchRequest
from backend.app.services.hybrid_retriever import HybridRetriever


def test_hybrid_retriever_returns_feature_cards_from_fts_index(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        _chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    retriever = HybridRetriever(index_path=index_path)

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "ok"
    assert response.cards[0].feature_name == "촬영 보조"
    assert response.cards[0].sources[0].document_id == "sample_manual"
    assert response.cards[0].sources[0].page == 12
    assert response.cards[0].supported_models[0].model_id == "DC-G9M2"


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
        _chunk(model_ids=("DC-TZ99", "DC-ZS99")).model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    retriever = HybridRetriever(index_path=index_path)

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-ZS99"]))

    assert response.retrieval_status == "ok"
    assert response.cards[0].sources[0].model_id == "DC-ZS99"


def test_hybrid_retriever_detects_model_name_in_query(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        _chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    retriever = HybridRetriever(
        index_path=index_path,
        models=(_model("DC-G9M2", "LUMIX G9II"),),
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
        _chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    retriever = HybridRetriever(
        index_path=index_path,
        models=(_model("DC-G9M2", "LUMIX G9II"),),
    )

    response = retriever.search(
        SearchRequest(query="G9M2에서 제브라 패턴 어디서 설정해?"),
    )

    assert response.retrieval_status == "ok"
    assert response.normalized_query.search_query == "제브라 패턴"
    assert response.cards[0].sources[0].model_id == "DC-G9M2"


def _chunk(
    *,
    model_ids: tuple[str, ...] = ("DC-G9M2",),
) -> ExtractedChunk:
    content = "제브라 패턴은 노출 확인에 사용하는 촬영 보조 기능입니다."
    return ExtractedChunk(
        chunk_id="sample_manual:opendl:12:1",
        document_id="sample_manual",
        model_ids=model_ids,
        page_start=12,
        page_end=12,
        section_title="촬영 보조",
        chunk_type="paragraph",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )


def _model(model_id: str, display_name: str) -> CameraModelRegistryEntry:
    return CameraModelRegistryEntry(
        model_id=model_id,
        display_name=display_name,
        product_line="LUMIX",
    )
