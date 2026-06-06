import json
from pathlib import Path

from backend.app.evaluation.search_eval import (
    SearchEvalReport,
    run_search_eval,
    write_search_eval_report,
)
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.fts_index import build_fts_index


def test_run_search_eval_reports_document_and_page_hit_rates(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample.jsonl").write_text(
        _chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
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
                    "top_k": 5,
                },
                {
                    "case_id": "miss",
                    "query": "없는 기능",
                    "model_ids": ["DC-G9M2"],
                    "expected_document_id": "sample_manual",
                    "expected_pages": [99],
                    "top_k": 5,
                },
            ],
        ),
        encoding="utf-8",
    )

    report = run_search_eval(cases_path=cases_path, index_path=index_path)

    assert report.case_count == 2
    assert report.document_hit_count == 1
    assert report.page_hit_count == 1
    assert report.document_hit_rate == 0.5
    assert report.page_hit_rate == 0.5


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
                    "top_k": 5,
                },
            ],
        ),
        encoding="utf-8",
    )

    report = run_search_eval(cases_path=cases_path, index_path=index_path)

    assert report.document_hit_count == 1
    assert report.page_hit_count == 0
    assert report.results[0].top_rank is None


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
