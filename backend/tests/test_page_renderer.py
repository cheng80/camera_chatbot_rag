from pathlib import Path

import pytest
from backend.app.indexing.page_renderer import (
    PageRenderRequest,
    render_pdf_page,
)
from pypdf import PdfWriter


def test_render_pdf_page_writes_png(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    output_root = tmp_path / "page_images"
    _write_sample_pdf(pdf_path)

    result = render_pdf_page(
        PageRenderRequest(
            document_id="sample_manual",
            pdf_path=pdf_path,
            page=1,
            output_root=output_root,
            manuals_root=tmp_path,
        ),
    )

    assert result.rendered is True
    assert result.image_path == output_root / "sample_manual" / "1.png"
    assert result.image_path.is_file()
    assert result.error is None


def test_render_pdf_page_reports_missing_pdf(tmp_path: Path) -> None:
    result = render_pdf_page(
        PageRenderRequest(
            document_id="missing_manual",
            pdf_path=tmp_path / "missing.pdf",
            page=1,
            output_root=tmp_path / "page_images",
            manuals_root=tmp_path,
        ),
    )

    assert result.rendered is False
    assert result.error is not None
    assert result.error.code == "missing_pdf"


def test_render_pdf_page_reports_page_out_of_range(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _write_sample_pdf(pdf_path)

    result = render_pdf_page(
        PageRenderRequest(
            document_id="sample_manual",
            pdf_path=pdf_path,
            page=2,
            output_root=tmp_path / "page_images",
            manuals_root=tmp_path,
        ),
    )

    assert result.rendered is False
    assert result.error is not None
    assert result.error.code == "page_out_of_range"


@pytest.mark.parametrize(
    "document_id",
    ["../escape", "nested/path", "/abs", "DC-S9"],
)
def test_render_pdf_page_rejects_unsafe_document_id(
    document_id: str,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    output_root = tmp_path / "page_images"
    _write_sample_pdf(pdf_path)

    result = render_pdf_page(
        PageRenderRequest(
            document_id=document_id,
            pdf_path=pdf_path,
            page=1,
            output_root=output_root,
            manuals_root=tmp_path,
        ),
    )

    assert result.rendered is False
    assert result.image_path == output_root / "_invalid" / "1.png"
    assert result.error is not None
    assert result.error.code == "unsafe_document_id"


def test_render_pdf_page_rejects_pdf_outside_manuals_root(tmp_path: Path) -> None:
    manuals_root = tmp_path / "manuals"
    manuals_root.mkdir()
    pdf_path = tmp_path / "outside.pdf"
    _write_sample_pdf(pdf_path)

    result = render_pdf_page(
        PageRenderRequest(
            document_id="sample_manual",
            pdf_path=pdf_path,
            page=1,
            output_root=tmp_path / "page_images",
            manuals_root=manuals_root,
        ),
    )

    assert result.rendered is False
    assert result.error is not None
    assert result.error.code == "unsafe_pdf_path"


def _write_sample_pdf(path: Path) -> None:
    writer = PdfWriter()
    _ = writer.add_blank_page(width=200, height=200)
    with path.open("wb") as output_file:
        _ = writer.write(output_file)
