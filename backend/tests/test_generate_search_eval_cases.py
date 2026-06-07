from pathlib import Path

from backend.app.evaluation.generate_search_eval_cases import (
    generate_search_eval_cases,
    write_search_eval_cases,
)
from backend.app.indexing.chunker import ExtractedChunk


def test_generate_search_eval_cases_uses_section_titles(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(
        chunks_dir / "sample.jsonl",
        (
            _chunk(section_title="[제브라 패턴]", page=415),
            _chunk(section_title="목차", page=5),
            _chunk(section_title="비디오 촬영하기 121", page=6),
            _chunk(section_title="메시지 표시 P325 문제해결 P328", page=1),
            _chunk(
                section_title=" 응결(렌즈 또는 모니터에 김이 서리는 경우)",
                page=19,
            ),
            _chunk(section_title="≥배터리 팩", page=20),
            _chunk(section_title="Wi-Fi 연결", page=673),
        ),
    )

    cases = generate_search_eval_cases(chunks_dir=chunks_dir, limit=10)

    assert len(cases) == 4
    assert cases[0].query == "제브라 패턴"
    assert cases[0].expected_pages == (415,)
    assert cases[0].source_method == "section_title_weak_label"
    assert cases[1].query == "응결(렌즈 또는 모니터에 김이 서리는 경우)"
    assert cases[2].query == "배터리 팩"
    assert cases[3].feature_category == "connectivity"


def test_write_search_eval_cases_writes_json(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(chunks_dir / "sample.jsonl", (_chunk(),))
    cases = generate_search_eval_cases(chunks_dir=chunks_dir, limit=1)

    output_path = write_search_eval_cases(
        cases=cases,
        path=tmp_path / "generated_search_eval_cases.json",
    )

    assert output_path.is_file()


def _write_chunks(path: Path, chunks: tuple[ExtractedChunk, ...]) -> None:
    _ = path.write_text(
        "\n".join(chunk.model_dump_json() for chunk in chunks) + "\n",
        encoding="utf-8",
    )


def _chunk(
    *,
    section_title: str = "제브라 패턴",
    page: int = 7,
) -> ExtractedChunk:
    content = f"{section_title} 설정"
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
