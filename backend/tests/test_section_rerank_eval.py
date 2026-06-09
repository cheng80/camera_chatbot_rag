from pathlib import Path

from backend.app.evaluation.search_eval_schema import SearchEvalCase
from backend.app.evaluation.section_rerank_eval import (
    SectionRerankEvalIndexPaths,
    run_section_rerank_eval_cases,
)
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.fts_index import build_fts_index
from backend.app.indexing.section_documents import SectionDocument
from backend.app.indexing.section_fts_index import build_section_fts_index
from backend.app.indexing.section_vector_index import build_section_vector_index


def test_run_section_rerank_eval_cases_compares_all_strategies(
    tmp_path: Path,
) -> None:
    chunk_index_path, section_fts_path, section_vector_path = _build_indexes(tmp_path)

    report = run_section_rerank_eval_cases(
        cases=(
            SearchEvalCase(
                case_id="focus_peaking",
                query="초점 피킹",
                model_ids=("DC-G9M2",),
                expected_document_id="sample",
                expected_pages=(12,),
                query_type="exact_keyword",
                feature_category="focus",
                difficulty="easy",
                source_method="manual_seed",
                top_k=2,
            ),
        ),
        index_paths=SectionRerankEvalIndexPaths(
            chunk_index_path=chunk_index_path,
            section_fts_index_path=section_fts_path,
            section_vector_index_path=section_vector_path,
        ),
    )

    by_strategy = {strategy.strategy: strategy.report for strategy in report.strategies}
    assert tuple(by_strategy) == (
        "chunk_fts",
        "section_fts",
        "section_vector",
        "chunk_section_guarded_rerank",
    )
    assert by_strategy["section_vector"].page_hit_rate == 1
    assert (
        by_strategy["chunk_section_guarded_rerank"].page_hit_rate
        >= by_strategy["chunk_fts"].page_hit_rate
    )


def _build_indexes(tmp_path: Path) -> tuple[Path, Path, Path]:
    chunks_dir = tmp_path / "chunks"
    sections_dir = tmp_path / "sections"
    chunks_dir.mkdir()
    sections_dir.mkdir()
    _ = (chunks_dir / "sample.jsonl").write_text(
        "\n".join(
            (
                _chunk(
                    chunk_id="sample:opendl:3:1",
                    page=3,
                    content="초점 피킹 초점 피킹 초점 피킹 일반 안내",
                ).model_dump_json(),
                _chunk(
                    chunk_id="sample:opendl:12:1",
                    page=12,
                    content="초점 피킹 설정 위치",
                ).model_dump_json(),
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    _ = (sections_dir / "sample.jsonl").write_text(
        _section().model_dump_json() + "\n",
        encoding="utf-8",
    )
    chunk_index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    section_fts_path = tmp_path / "section_fts" / "sections.sqlite3"
    section_vector_path = tmp_path / "section_vector" / "index.jsonl"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=chunk_index_path)
    _ = build_section_fts_index(
        sections_dir=sections_dir,
        index_path=section_fts_path,
    )
    _ = build_section_vector_index(
        sections_dir=sections_dir,
        index_path=section_vector_path,
    )
    return chunk_index_path, section_fts_path, section_vector_path


def _chunk(*, chunk_id: str, page: int, content: str) -> ExtractedChunk:
    return ExtractedChunk(
        chunk_id=chunk_id,
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


def _section() -> SectionDocument:
    return SectionDocument(
        section_id="sample:section:12:focus",
        document_id="sample",
        model_ids=("DC-G9M2",),
        page_start=12,
        page_end=12,
        section_title="초점 피킹",
        content="초점 피킹 설정 위치와 표시 방법입니다.",
        source_chunk_ids=("sample:opendl:12:1",),
        source_hash="0" * 64,
    )
