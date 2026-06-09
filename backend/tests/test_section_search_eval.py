from pathlib import Path

from backend.app.evaluation.search_eval_schema import SearchEvalCase
from backend.app.evaluation.section_search_eval import run_section_search_eval_cases
from backend.app.indexing.section_documents import SectionDocument
from backend.app.indexing.section_fts_index import build_section_fts_index


def test_run_section_search_eval_cases_scores_document_and_page_hits(
    tmp_path: Path,
) -> None:
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    _ = (sections_dir / "sample.jsonl").write_text(
        _section().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "sections.sqlite3"
    _ = build_section_fts_index(sections_dir=sections_dir, index_path=index_path)

    report = run_section_search_eval_cases(
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
            ),
        ),
        index_path=index_path,
    )

    assert report.case_count == 1
    assert report.document_hit_rate == 1
    assert report.page_hit_rate == 1
    assert report.results[0].top_rank == 1


def _section() -> SectionDocument:
    return SectionDocument(
        section_id="sample:section:12:focus",
        document_id="sample",
        model_ids=("DC-G9M2",),
        page_start=12,
        page_end=12,
        section_title="초점 피킹",
        content="초점 피킹은 초점 영역의 윤곽을 색으로 표시합니다.",
        source_chunk_ids=("sample:opendl:12:1",),
        source_hash="0" * 64,
    )
