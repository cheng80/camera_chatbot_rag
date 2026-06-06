from pathlib import Path

from backend.app.indexing.pdf_extractor import (
    extract_document_pages,
    write_document_pages_jsonl,
)
from backend.app.schemas.document import ManualDocumentRegistryEntry
from pypdf import PdfWriter


def test_extract_document_pages_reads_pdf_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    _ = writer.add_blank_page(width=200, height=200)
    with pdf_path.open("wb") as pdf_file:
        _ = writer.write(pdf_file)
    registry_entry = ManualDocumentRegistryEntry(
        document_id="sample_manual",
        title="Sample Manual",
        filename=pdf_path.name,
        model_ids=("DC-G9M2",),
        language="ko",
        document_type="full_manual",
    )

    pages = extract_document_pages(document=registry_entry, pdf_path=pdf_path)

    assert len(pages) == 1
    assert pages[0].document_id == "sample_manual"
    assert pages[0].model_ids == ("DC-G9M2",)
    assert pages[0].page == 1
    assert pages[0].text == ""
    assert pages[0].char_count == 0


def test_write_document_pages_jsonl_writes_one_json_per_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    output_dir = tmp_path / "pages"
    writer = PdfWriter()
    _ = writer.add_blank_page(width=200, height=200)
    with pdf_path.open("wb") as pdf_file:
        _ = writer.write(pdf_file)
    registry_entry = ManualDocumentRegistryEntry(
        document_id="sample_manual",
        title="Sample Manual",
        filename=pdf_path.name,
        model_ids=("DC-G9M2",),
        language="ko",
        document_type="full_manual",
    )
    pages = extract_document_pages(document=registry_entry, pdf_path=pdf_path)

    output_path = write_document_pages_jsonl(pages=pages, output_dir=output_dir)

    assert output_path == output_dir / "sample_manual.jsonl"
    assert output_path.read_text(encoding="utf-8").count("\n") == 1
    assert '"document_id":"sample_manual"' in output_path.read_text(encoding="utf-8")
