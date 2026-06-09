from pathlib import Path

from backend.app.evaluation.semantic_search_eval_cases import (
    generate_semantic_search_eval_cases,
)
from backend.app.indexing.chunker import ExtractedChunk


def test_generate_semantic_search_eval_cases_uses_content_keywords(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(
        chunks_dir / "sample.jsonl",
        (
            _chunk(
                page=12,
                section_title="기본 조작",
                content="제브라 패턴 휘도 레벨 과다 노출 표시",
            ),
            _chunk(
                page=13,
                section_title="목차",
                content="제브라 패턴........12",
            ),
            _chunk(
                page=14,
                section_title="배터리",
                content="배터리 배터리 충전 램프 USB 전원",
            ),
        ),
    )

    cases = generate_semantic_search_eval_cases(chunks_dir=chunks_dir, limit=10)

    assert len(cases) == 2
    assert cases[0].query == "제브라 패턴 휘도 레벨"
    assert cases[0].query_type == "semantic_keyword"
    assert cases[0].source_method == "semantic_keyword_weak_label"
    assert cases[1].query == "배터리 충전 램프 USB"


def _write_chunks(path: Path, chunks: tuple[ExtractedChunk, ...]) -> None:
    _ = path.write_text(
        "\n".join(chunk.model_dump_json() for chunk in chunks) + "\n",
        encoding="utf-8",
    )


def _chunk(*, page: int, section_title: str, content: str) -> ExtractedChunk:
    return ExtractedChunk(
        chunk_id=f"sample_manual:page:{page}",
        document_id="sample_manual",
        model_ids=("DC-G9M2",),
        page_start=page,
        page_end=page,
        section_title=section_title,
        chunk_type="paragraph",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )
