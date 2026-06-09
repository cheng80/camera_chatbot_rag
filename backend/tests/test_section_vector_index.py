from pathlib import Path

from backend.app.indexing.section_documents import SectionDocument
from backend.app.indexing.section_vector_index import (
    build_section_vector_index,
    search_section_vector_index,
)


def test_build_section_vector_index_searches_sections(tmp_path: Path) -> None:
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    _write_sections(
        sections_dir / "sample.jsonl",
        (
            _section(content="초점 피킹은 초점 영역의 윤곽을 표시합니다."),
            _section(
                section_id="sample:section:2:stabilizer",
                page=2,
                section_title="손떨림 보정",
                content="손떨림 보정 설정입니다.",
            ),
        ),
    )
    index_path = tmp_path / "section_vector" / "index.jsonl"

    report = build_section_vector_index(
        sections_dir=sections_dir,
        index_path=index_path,
    )
    results = search_section_vector_index(index_path=index_path, query="초점 피킹")

    assert report.section_count == 2
    assert report.document_count == 1
    assert results[0].section_id == "sample:section:1:focus"
    assert results[0].page_start == 1


def test_search_section_vector_index_applies_model_filter(tmp_path: Path) -> None:
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    _write_sections(
        sections_dir / "sample.jsonl",
        (
            _section(model_ids=("DC-G9M2",)),
            _section(
                section_id="sample:section:2:focus",
                page=2,
                model_ids=("DC-S1M2",),
            ),
        ),
    )
    index_path = tmp_path / "section_vector" / "index.jsonl"
    _ = build_section_vector_index(sections_dir=sections_dir, index_path=index_path)

    results = search_section_vector_index(
        index_path=index_path,
        query="초점",
        model_ids=("DC-S1M2",),
    )

    assert len(results) == 1
    assert results[0].model_ids == ("DC-S1M2",)
    assert results[0].page_start == 2


def _write_sections(path: Path, sections: tuple[SectionDocument, ...]) -> None:
    _ = path.write_text(
        "\n".join(section.model_dump_json() for section in sections) + "\n",
        encoding="utf-8",
    )


def _section(
    *,
    section_id: str = "sample:section:1:focus",
    page: int = 1,
    section_title: str = "초점 피킹",
    content: str = "초점 피킹 설정입니다.",
    model_ids: tuple[str, ...] = ("DC-G9M2",),
) -> SectionDocument:
    return SectionDocument(
        section_id=section_id,
        document_id="sample",
        model_ids=model_ids,
        page_start=page,
        page_end=page,
        section_title=section_title,
        content=content,
        source_chunk_ids=("sample:opendl:1:1",),
        source_hash="0" * 64,
    )
