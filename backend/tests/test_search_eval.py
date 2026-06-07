import json
from pathlib import Path

import pytest
from backend.app.evaluation.search_eval import (
    run_search_eval,
    run_search_eval_cases,
    write_search_eval_report,
)
from backend.app.evaluation.search_eval_schema import SearchEvalCase, SearchEvalReport
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.fts_index import build_fts_index
from backend.app.indexing.pdf_extractor import ExtractedPage
from pydantic import ValidationError


def test_run_search_eval_reports_document_and_page_hit_rates(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample.jsonl").write_text(
        _chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = _write_source_validation_fixture(
        tmp_path=tmp_path,
        pages=(7,),
    )
    cases_path = tmp_path / "search_eval_cases.json"
    _ = cases_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "zebra",
                    "query": "제브라패턴",
                    "model_ids": ["DC-G9M2"],
                    "expected_document_id": "sample_manual",
                    "expected_pages": [7],
                    "query_type": "compact_korean",
                    "feature_category": "exposure",
                    "difficulty": "medium",
                    "source_method": "manual_seed",
                    "top_k": 5,
                },
                {
                    "case_id": "miss",
                    "query": "없는 기능",
                    "model_ids": ["DC-G9M2"],
                    "expected_document_id": "sample_manual",
                    "expected_pages": [99],
                    "query_type": "natural_language",
                    "feature_category": "general",
                    "difficulty": "easy",
                    "source_method": "manual_seed",
                    "top_k": 5,
                },
            ],
        ),
        encoding="utf-8",
    )

    report = run_search_eval(
        cases_path=cases_path,
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert report.case_count == 2
    assert report.document_hit_count == 1
    assert report.page_hit_count == 1
    assert report.document_hit_rate == 0.5
    assert report.page_hit_rate == 0.5
    assert report.by_query_type[0].group_name == "compact_korean"
    assert report.by_query_type[0].page_hit_rate == 1
    assert report.by_feature_category[0].group_name == "exposure"
    assert report.by_difficulty[0].group_name == "easy"
    assert report.by_difficulty[1].group_name == "medium"


def test_run_search_eval_requires_page_hit_in_expected_document(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    chunks = (_chunk(document_id="other_manual", page_start=7), _chunk(page_start=8))
    _ = (chunks_dir / "sample.jsonl").write_text(
        "".join(chunk.model_dump_json() + "\n" for chunk in chunks),
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = _write_source_validation_fixture(
        tmp_path=tmp_path,
        pages=(7, 8),
        document_ids=("sample_manual", "other_manual"),
    )
    cases_path = tmp_path / "search_eval_cases.json"
    _ = cases_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "same_page_wrong_document",
                    "query": "제브라패턴",
                    "model_ids": ["DC-G9M2"],
                    "expected_document_id": "sample_manual",
                    "expected_pages": [7],
                    "query_type": "compact_korean",
                    "feature_category": "exposure",
                    "difficulty": "medium",
                    "source_method": "manual_seed",
                    "top_k": 5,
                },
            ],
        ),
        encoding="utf-8",
    )

    report = run_search_eval(
        cases_path=cases_path,
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert report.document_hit_count == 1
    assert report.page_hit_count == 0
    assert report.results[0].top_rank is None


def test_run_search_eval_cases_uses_loaded_case_sequence(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample.jsonl").write_text(
        _chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = _write_source_validation_fixture(
        tmp_path=tmp_path,
        pages=(7,),
    )

    report = run_search_eval_cases(
        cases=(
            SearchEvalCase(
                case_id="zebra",
                query="제브라패턴",
                model_ids=("DC-G9M2",),
                expected_document_id="sample_manual",
                expected_pages=(7,),
                query_type="compact_korean",
                feature_category="exposure",
                difficulty="medium",
                source_method="manual_seed",
                top_k=5,
            ),
        ),
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert report.case_count == 1
    assert report.page_hit_rate == 1


def test_write_search_eval_report_writes_json(tmp_path: Path) -> None:
    report = SearchEvalReport(
        case_count=0,
        document_hit_count=0,
        page_hit_count=0,
        document_hit_rate=0,
        page_hit_rate=0,
        results=(),
    )

    output_path = write_search_eval_report(
        report=report,
        path=tmp_path / "reports" / "search_eval_report.json",
    )

    assert output_path.is_file()


def test_search_eval_case_rejects_unknown_metadata() -> None:
    payload = {
        "case_id": "bad",
        "query": "제브라",
        "expected_document_id": "sample_manual",
        "expected_pages": [7],
        "query_type": "typo",
        "feature_category": "exposure",
        "difficulty": "easy",
        "source_method": "manual_seed",
        "unknown": "field",
    }

    with pytest.raises(ValidationError):
        _ = SearchEvalCase.model_validate(payload)


def _chunk(
    *,
    document_id: str = "sample_manual",
    page_start: int = 7,
) -> ExtractedChunk:
    content = "제브라 패턴 설정"
    return ExtractedChunk(
        chunk_id=f"{document_id}:page:{page_start}",
        document_id=document_id,
        model_ids=("DC-G9M2",),
        page_start=page_start,
        page_end=page_start,
        section_title="제브라 패턴",
        chunk_type="page",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )


def _write_source_validation_fixture(
    *,
    tmp_path: Path,
    pages: tuple[int, ...],
    document_ids: tuple[str, ...] = ("sample_manual",),
) -> tuple[Path, Path]:
    registry_dir = tmp_path / "registry"
    pages_dir = tmp_path / "pages"
    registry_dir.mkdir()
    pages_dir.mkdir()
    _ = (registry_dir / "models.json").write_text(
        json.dumps(
            [
                {
                    "model_id": "DC-G9M2",
                    "display_name": "LUMIX G9II",
                    "product_line": "LUMIX G",
                },
            ],
        ),
        encoding="utf-8",
    )
    _ = (registry_dir / "documents.json").write_text(
        json.dumps(
            [
                {
                    "document_id": document_id,
                    "title": "Sample Manual",
                    "filename": f"{document_id}.pdf",
                    "model_ids": ["DC-G9M2"],
                    "language": "ko",
                    "document_type": "full_manual",
                }
                for document_id in document_ids
            ],
        ),
        encoding="utf-8",
    )
    for document_id in document_ids:
        lines = [
            ExtractedPage(
                document_id=document_id,
                model_ids=("DC-G9M2",),
                page=page,
                text=f"page {page}",
                char_count=7,
            ).model_dump_json()
            for page in pages
        ]
        _ = (pages_dir / f"{document_id}.jsonl").write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
    return registry_dir, pages_dir
