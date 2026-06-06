import json
from pathlib import Path

from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.pdf_extractor import ExtractedPage


def community_chunk() -> ExtractedChunk:
    content = "제브라 패턴은 노출 확인에 사용하는 촬영 보조 기능입니다."
    return ExtractedChunk(
        chunk_id="sample_manual:opendl:12:1",
        document_id="sample_manual",
        model_ids=("DC-G9M2",),
        page_start=12,
        page_end=12,
        section_title="촬영 보조",
        chunk_type="paragraph",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )


def write_community_source_validation_fixture(*, tmp_path: Path) -> tuple[Path, Path]:
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
                    "document_id": "sample_manual",
                    "title": "Sample Manual",
                    "filename": "sample_manual.pdf",
                    "model_ids": ["DC-G9M2"],
                    "language": "ko",
                    "document_type": "full_manual",
                },
            ],
        ),
        encoding="utf-8",
    )
    page = ExtractedPage(
        document_id="sample_manual",
        model_ids=("DC-G9M2",),
        page=12,
        text="page 12",
        char_count=7,
    )
    _ = (pages_dir / "sample_manual.jsonl").write_text(
        page.model_dump_json() + "\n",
        encoding="utf-8",
    )
    return registry_dir, pages_dir
