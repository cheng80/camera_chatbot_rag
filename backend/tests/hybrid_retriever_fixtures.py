import json
from pathlib import Path

from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.pdf_extractor import ExtractedPage
from backend.app.schemas.document import CameraModelRegistryEntry


def hybrid_chunk(
    *,
    chunk_id: str = "sample_manual:opendl:12:1",
    model_ids: tuple[str, ...] = ("DC-G9M2",),
) -> ExtractedChunk:
    content = "제브라 패턴은 노출 확인에 사용하는 촬영 보조 기능입니다."
    return ExtractedChunk(
        chunk_id=chunk_id,
        document_id="sample_manual",
        model_ids=model_ids,
        page_start=12,
        page_end=12,
        section_title="촬영 보조",
        chunk_type="paragraph",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )


def hybrid_model(model_id: str, display_name: str) -> CameraModelRegistryEntry:
    return CameraModelRegistryEntry(
        model_id=model_id,
        display_name=display_name,
        product_line="LUMIX",
    )


def write_hybrid_source_validation_fixture(
    *,
    tmp_path: Path,
    pages: tuple[int, ...] = (12,),
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
                {
                    "model_id": "DC-ZS99",
                    "display_name": "LUMIX ZS99",
                    "product_line": "LUMIX TZ",
                },
                {
                    "model_id": "DC-TZ99",
                    "display_name": "LUMIX TZ99",
                    "product_line": "LUMIX TZ",
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
                    "model_ids": ["DC-G9M2", "DC-ZS99", "DC-TZ99"],
                    "language": "ko",
                    "document_type": "full_manual",
                },
            ],
        ),
        encoding="utf-8",
    )
    page_lines = [
        ExtractedPage(
            document_id="sample_manual",
            model_ids=("DC-G9M2", "DC-ZS99", "DC-TZ99"),
            page=page,
            text=f"page {page}",
            char_count=7,
        ).model_dump_json()
        for page in pages
    ]
    _ = (pages_dir / "sample_manual.jsonl").write_text(
        "\n".join(page_lines) + "\n",
        encoding="utf-8",
    )
    return registry_dir, pages_dir
