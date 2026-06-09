from pathlib import Path

from backend.app.evaluation.chunk_quality_audit import (
    run_chunk_quality_audit,
    write_chunk_quality_audit_report,
)
from backend.app.indexing.chunker import ExtractedChunk, write_document_chunks_jsonl


def test_run_chunk_quality_audit_flags_broken_titles_and_references(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    _ = write_document_chunks_jsonl(
        chunks=(
            _chunk(chunk_id="sample:opendl:1:1", section_title="이미지 품질"),
            _chunk(
                chunk_id="sample:opendl:2:1",
                page=2,
                section_title="1",
                content="• [초점 피킹](초점 피킹 235\n)",
            ),
            _chunk(
                chunk_id="sample:opendl:3:1",
                page=3,
                section_title="\N{MULTIPLICATION SIGN}",
                content="\N{MULTIPLICATION SIGN}",
            ),
        ),
        document_id="sample",
        output_dir=chunks_dir,
    )

    report = run_chunk_quality_audit(chunks_dir=chunks_dir)

    assert report.document_count == 1
    assert report.chunk_count == 3
    assert report.issue_chunk_count == 2
    assert report.issue_counts["bad_section_title"] == 2
    assert report.issue_counts["internal_page_reference"] == 1
    assert report.issue_counts["tiny_chunk"] == 1
    assert [example.chunk_id for example in report.examples] == [
        "sample:opendl:2:1",
        "sample:opendl:3:1",
    ]


def test_run_chunk_quality_audit_reports_section_readiness(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    _ = write_document_chunks_jsonl(
        chunks=(
            _chunk(chunk_id="sample:opendl:1:1", section_title="초점 피킹"),
            _chunk(
                chunk_id="sample:opendl:1:2",
                section_title="초점 피킹",
                content="설정",
            ),
            _chunk(
                chunk_id="sample:opendl:2:1",
                page=2,
                section_title=None,
                content="제목 없이 추출된 본문입니다.",
            ),
            _chunk(
                chunk_id="sample:opendl:3:1",
                page=3,
                section_title="색인",
                content="AF .......... 12",
            ),
            _chunk(
                chunk_id="sample:opendl:4:1",
                page=4,
                section_title="재생 화면",
                content="G",
            ),
            _chunk(
                chunk_id="sample:opendl:4:2",
                page=4,
                section_title="재생 화면",
                content="B",
            ),
            _chunk(
                chunk_id="sample:opendl:4:3",
                page=4,
                section_title="재생 화면",
                content="R",
            ),
            _chunk(
                chunk_id="sample:opendl:4:4",
                page=4,
                section_title="재생 화면",
                content="Y",
            ),
            _chunk(
                chunk_id="sample:opendl:4:5",
                page=4,
                section_title="재생 화면",
                content="초점 위치 표시 설명입니다.",
            ),
        ),
        document_id="sample",
        output_dir=chunks_dir,
    )

    report = run_chunk_quality_audit(chunks_dir=chunks_dir)

    assert report.section_readiness.chunk_count == 9
    assert report.section_readiness.ready_chunk_count == 2
    assert report.section_readiness.missing_section_title_chunk_count == 1
    assert report.section_readiness.toc_or_index_chunk_count == 1
    assert report.section_readiness.tiny_chunk_count == 4
    assert report.section_readiness.fragmented_section_group_count == 1
    assert report.section_readiness.section_group_count == 2


def test_write_chunk_quality_audit_report_writes_json(tmp_path: Path) -> None:
    report = run_chunk_quality_audit(chunks_dir=tmp_path / "missing")
    output_path = tmp_path / "report.json"

    written_path = write_chunk_quality_audit_report(report=report, path=output_path)

    assert written_path == output_path
    assert '"chunk_count": 0' in output_path.read_text(encoding="utf-8")


def _chunk(
    *,
    chunk_id: str = "sample:opendl:1:1",
    page: int = 1,
    section_title: str | None = "초점 피킹",
    content: str = "초점 피킹 설정입니다.",
) -> ExtractedChunk:
    return ExtractedChunk(
        chunk_id=chunk_id,
        document_id="sample",
        model_ids=("DC-S1",),
        page_start=page,
        page_end=page,
        section_title=section_title,
        chunk_type="paragraph",
        content=content,
        char_count=len(content),
        source_hash="a" * 64,
    )
