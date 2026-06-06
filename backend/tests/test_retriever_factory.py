from pathlib import Path

from backend.app.core.settings import Settings
from backend.app.indexing.fts_index import build_fts_index
from backend.app.schemas.search import SearchRequest
from backend.app.services.retriever_factory import build_hybrid_retriever
from backend.tests.hybrid_retriever_fixtures import (
    hybrid_chunk,
    write_hybrid_source_validation_fixture,
)


def test_build_hybrid_retriever_uses_local_vector_when_enabled(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    chunks_dir = data_dir / "processed" / "chunks"
    chunks_dir.mkdir(parents=True)
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        hybrid_chunk(
            chunk_id="sample_manual:vector:13:1",
            model_ids=("DC-G9M2",),
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    index_path = data_dir / "indexes" / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_hybrid_source_validation_fixture(
        tmp_path=data_dir,
        pages=(12,),
    )
    assert registry_dir == data_dir / "registry"
    assert pages_dir == data_dir / "pages"
    processed_pages_dir = data_dir / "processed" / "pages"
    processed_pages_dir.mkdir(parents=True)
    _ = (processed_pages_dir / "sample_manual.jsonl").write_text(
        (data_dir / "pages" / "sample_manual.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    retriever = build_hybrid_retriever(
        settings=Settings(data_dir=data_dir, enable_local_vector=True),
    )

    response = retriever.search(SearchRequest(query="제브라", model_ids=["DC-G9M2"]))

    assert response.retrieval_status == "ok"
    assert response.cards[0].sources[0].document_id == "sample_manual"
