import json
from pathlib import Path

import pytest
from backend.app.indexing.pdf_extractor import ExtractedPage
from backend.app.wiki.source_ref_checker import (
    SourceReferenceCandidate,
    validate_source_reference,
)


def test_validate_source_reference_accepts_official_page(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    pages_dir = tmp_path / "pages"
    registry_dir.mkdir()
    pages_dir.mkdir()
    _write_registry(registry_dir)
    _write_pages(pages_dir=pages_dir, document_id="dc_g9m2_full_kor", pages=(1, 415))

    result = validate_source_reference(
        SourceReferenceCandidate(
            document_id="dc_g9m2_full_kor",
            model_id="DC-G9M2",
            page=415,
        ),
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert result.valid is True
    assert result.errors == ()
    assert result.viewer_url == "/api/viewer/dc_g9m2_full_kor/pages/415"


def test_validate_source_reference_reports_structured_failures(
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "registry"
    pages_dir = tmp_path / "pages"
    registry_dir.mkdir()
    pages_dir.mkdir()
    _write_registry(registry_dir)
    _write_pages(pages_dir=pages_dir, document_id="dc_g9m2_full_kor", pages=(1,))

    result = validate_source_reference(
        SourceReferenceCandidate(
            document_id="dc_g9m2_full_kor",
            model_id="DC-S1M2",
            page=415,
        ),
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert result.valid is False
    assert tuple(error.code for error in result.errors) == (
        "document_model_mismatch",
        "page_out_of_range",
    )
    assert result.viewer_url is None


def test_validate_source_reference_reports_missing_processed_pages(
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "registry"
    pages_dir = tmp_path / "pages"
    registry_dir.mkdir()
    pages_dir.mkdir()
    _write_registry(registry_dir)

    result = validate_source_reference(
        SourceReferenceCandidate(
            document_id="dc_g9m2_full_kor",
            model_id="DC-G9M2",
            page=1,
        ),
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert result.valid is False
    assert tuple(error.code for error in result.errors) == ("processed_pages_missing",)


@pytest.mark.parametrize(
    "document_id",
    ["../escape", "nested/path", "/abs", "DC-S9"],
)
def test_validate_source_reference_rejects_unsafe_document_id(
    document_id: str,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "registry"
    pages_dir = tmp_path / "pages"
    registry_dir.mkdir()
    pages_dir.mkdir()
    _write_registry(registry_dir)
    outside_path = tmp_path / "escape.jsonl"
    _ = outside_path.write_text("should not be read", encoding="utf-8")

    result = validate_source_reference(
        SourceReferenceCandidate(
            document_id=document_id,
            model_id="DC-G9M2",
            page=1,
        ),
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert result.valid is False
    assert tuple(error.code for error in result.errors) == ("unsafe_document_id",)
    assert result.viewer_url is None


def test_validate_source_reference_sees_updated_processed_pages(
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "registry"
    pages_dir = tmp_path / "pages"
    registry_dir.mkdir()
    pages_dir.mkdir()
    _write_registry(registry_dir)
    _write_pages(pages_dir=pages_dir, document_id="dc_g9m2_full_kor", pages=(7,))

    first_result = validate_source_reference(
        SourceReferenceCandidate(
            document_id="dc_g9m2_full_kor",
            model_id="DC-G9M2",
            page=12,
        ),
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )
    _write_pages(pages_dir=pages_dir, document_id="dc_g9m2_full_kor", pages=(12,))

    second_result = validate_source_reference(
        SourceReferenceCandidate(
            document_id="dc_g9m2_full_kor",
            model_id="DC-G9M2",
            page=12,
        ),
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert first_result.valid is False
    assert second_result.valid is True


def _write_registry(registry_dir: Path) -> None:
    _ = (registry_dir / "models.json").write_text(
        json.dumps(
            [
                {
                    "model_id": "DC-G9M2",
                    "display_name": "LUMIX G9II",
                    "product_line": "LUMIX G",
                },
                {
                    "model_id": "DC-S1M2",
                    "display_name": "LUMIX S1II",
                    "product_line": "LUMIX S",
                },
            ],
        ),
        encoding="utf-8",
    )
    _ = (registry_dir / "documents.json").write_text(
        json.dumps(
            [
                {
                    "document_id": "dc_g9m2_full_kor",
                    "title": "DC-G9M2 전체 안내서",
                    "filename": "DC-G9M2_DVQP3025_full_kor.pdf",
                    "model_ids": ["DC-G9M2"],
                    "language": "ko",
                    "document_type": "full_manual",
                }
            ],
        ),
        encoding="utf-8",
    )


def _write_pages(*, pages_dir: Path, document_id: str, pages: tuple[int, ...]) -> None:
    lines = [
        ExtractedPage(
            document_id=document_id,
            model_ids=("DC-G9M2",),
            page=page,
            text=f"page {page}",
            char_count=6,
        ).model_dump_json()
        for page in pages
    ]
    _ = (pages_dir / f"{document_id}.jsonl").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
