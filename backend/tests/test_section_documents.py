from pathlib import Path

from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.section_documents import (
    build_section_documents,
    load_section_documents,
    write_section_documents_jsonl,
)


def test_build_section_documents_groups_chunks_by_page_and_title() -> None:
    documents = build_section_documents(
        chunks=(
            _chunk(
                chunk_id="sample:opendl:10:1",
                page=10,
                content="초점 피킹 설명입니다.",
            ),
            _chunk(
                chunk_id="sample:opendl:10:2",
                page=10,
                content="윤곽을 색으로 표시합니다.",
            ),
            _chunk(
                chunk_id="sample:opendl:11:1",
                page=11,
                section_title="초점 피킹",
                content="다른 페이지의 설정입니다.",
            ),
        ),
    )

    assert len(documents) == 2
    assert documents[0].document_id == "sample"
    assert documents[0].page_start == 10
    assert documents[0].section_title == "초점 피킹"
    assert documents[0].content == "초점 피킹 설명입니다.\n윤곽을 색으로 표시합니다."
    assert documents[0].source_chunk_ids == (
        "sample:opendl:10:1",
        "sample:opendl:10:2",
    )


def test_build_section_documents_excludes_unstable_source_chunks() -> None:
    documents = build_section_documents(
        chunks=(
            _chunk(chunk_id="sample:opendl:1:1", section_title=None),
            _chunk(
                chunk_id="sample:opendl:2:1",
                page=2,
                section_title="색인",
                content="AF .......... 12",
            ),
            _chunk(
                chunk_id="sample:opendl:3:1",
                page=3,
                section_title="재생 화면",
                content="G",
            ),
            _chunk(
                chunk_id="sample:opendl:4:1",
                page=4,
                content="충분한 본문 설명입니다.",
            ),
        ),
    )

    assert len(documents) == 1
    assert documents[0].page_start == 4


def test_write_and_load_section_documents_jsonl(tmp_path: Path) -> None:
    sections_dir = tmp_path / "sections"
    documents = build_section_documents(
        chunks=(
            _chunk(chunk_id="sample:opendl:1:1"),
            _chunk(chunk_id="other:opendl:1:1", document_id="other"),
        ),
    )

    written_path = write_section_documents_jsonl(
        section_documents=documents,
        document_id="sample",
        output_dir=sections_dir,
    )
    loaded = tuple(load_section_documents(sections_dir=sections_dir))

    assert written_path == sections_dir / "sample.jsonl"
    assert len(loaded) == 1
    assert loaded[0].document_id == "sample"


def _chunk(
    *,
    chunk_id: str = "sample:opendl:1:1",
    document_id: str = "sample",
    page: int = 1,
    section_title: str | None = "초점 피킹",
    content: str = "초점 피킹 설정입니다.",
) -> ExtractedChunk:
    return ExtractedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        model_ids=("DC-G9M2",),
        page_start=page,
        page_end=page,
        section_title=section_title,
        chunk_type="paragraph",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )
