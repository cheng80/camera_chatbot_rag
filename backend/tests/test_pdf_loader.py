from pathlib import Path

import pytest
from backend.app.indexing import opendataloader_runner, pdf_loader
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.pdf_extractor import ExtractedPage
from backend.app.schemas.document import ManualDocumentRegistryEntry

type ExtractionOutcome = tuple[tuple[ExtractedPage, ...], tuple[ExtractedChunk, ...]]


def test_extract_document_pages_primary_uses_opendataloader_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_entry = _registry_entry()
    expected_pages = (
        ExtractedPage(
            document_id="sample_manual",
            model_ids=("DC-TZ99",),
            page=1,
            text="목차",
            char_count=2,
        ),
    )
    expected_chunks = (
        ExtractedChunk(
            chunk_id="sample_manual:opendl:1:1",
            document_id="sample_manual",
            model_ids=("DC-TZ99",),
            page_start=1,
            page_end=1,
            section_title=None,
            chunk_type="heading",
            content="목차",
            char_count=2,
            source_hash="0" * 64,
        ),
    )

    def fake_extract_with_opendataloader(
        *,
        document: ManualDocumentRegistryEntry,
        pdf_path: Path,
    ) -> ExtractionOutcome:
        assert document == registry_entry
        assert pdf_path == Path("sample.pdf")
        return expected_pages, expected_chunks

    monkeypatch.setattr(
        pdf_loader,
        "_extract_with_opendataloader",
        fake_extract_with_opendataloader,
    )

    result = pdf_loader.extract_document_pages_primary(
        document=registry_entry,
        pdf_path=Path("sample.pdf"),
    )

    assert result.loader == "opendataloader"
    assert result.pages == expected_pages
    assert result.chunks == expected_chunks
    assert result.chunk_count == 1
    assert result.fallback_reason is None


@pytest.mark.parametrize(
    "error",
    [
        opendataloader_runner.OpenDataLoaderExtractionError.cli_failed("boom"),
        opendataloader_runner.OpenDataLoaderExtractionError.cli_not_found(),
    ],
)
def test_extract_document_pages_primary_falls_back_for_allowed_cli_errors(
    error: opendataloader_runner.OpenDataLoaderExtractionError,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_entry = _registry_entry()
    expected_pages = (
        ExtractedPage(
            document_id="sample_manual",
            model_ids=("DC-TZ99",),
            page=1,
            text="fallback",
            char_count=8,
        ),
    )

    def fake_extract_with_opendataloader(
        *,
        document: ManualDocumentRegistryEntry,
        pdf_path: Path,
    ) -> ExtractionOutcome:
        assert document == registry_entry
        assert pdf_path == Path("sample.pdf")
        raise error

    def fake_extract_document_pages(
        *,
        document: ManualDocumentRegistryEntry,
        pdf_path: Path,
    ) -> tuple[ExtractedPage, ...]:
        assert document == registry_entry
        assert pdf_path == Path("sample.pdf")
        return expected_pages

    monkeypatch.setattr(
        pdf_loader,
        "_extract_with_opendataloader",
        fake_extract_with_opendataloader,
    )
    monkeypatch.setattr(
        pdf_loader,
        "extract_document_pages",
        fake_extract_document_pages,
    )

    result = pdf_loader.extract_document_pages_primary(
        document=registry_entry,
        pdf_path=Path("sample.pdf"),
    )

    assert result.loader == "pypdf"
    assert result.pages == expected_pages
    assert result.chunk_count == 1
    assert result.fallback_reason == error.reason


@pytest.mark.parametrize(
    "error",
    [
        opendataloader_runner.OpenDataLoaderExtractionError.empty_pages(),
        opendataloader_runner.OpenDataLoaderExtractionError.missing_json(),
        opendataloader_runner.OpenDataLoaderExtractionError.no_pages(),
        opendataloader_runner.OpenDataLoaderExtractionError.page_count_mismatch(
            extracted=1,
            expected=2,
        ),
        opendataloader_runner.OpenDataLoaderExtractionError.timeout(),
    ],
)
def test_extract_document_pages_primary_does_not_fallback_on_integrity_errors(
    error: opendataloader_runner.OpenDataLoaderExtractionError,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_entry = _registry_entry()

    def fake_extract_with_opendataloader(
        *,
        document: ManualDocumentRegistryEntry,
        pdf_path: Path,
    ) -> ExtractionOutcome:
        assert document == registry_entry
        assert pdf_path == Path("sample.pdf")
        raise error

    monkeypatch.setattr(
        pdf_loader,
        "_extract_with_opendataloader",
        fake_extract_with_opendataloader,
    )

    with pytest.raises(
        opendataloader_runner.OpenDataLoaderExtractionError,
        match=error.reason,
    ):
        _ = pdf_loader.extract_document_pages_primary(
            document=registry_entry,
            pdf_path=Path("sample.pdf"),
        )


def test_write_pdf_loader_metadata_records_fallback_reason(tmp_path: Path) -> None:
    result = pdf_loader.PdfLoaderResult(
        loader="pypdf",
        pages=(
            ExtractedPage(
                document_id="sample_manual",
                model_ids=("DC-TZ99",),
                page=1,
                text="fallback",
                char_count=8,
            ),
        ),
        chunk_count=0,
        fallback_reason="cli exited with non-zero status",
    )

    output_path = pdf_loader.write_pdf_loader_metadata(
        result=result,
        output_dir=tmp_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert output_path.name == "sample_manual.loader.json"
    assert '"loader":"pypdf"' in content
    assert '"fallback_reason":"cli exited with non-zero status"' in content


def test_complete_page_sequence_fills_missing_blank_pages() -> None:
    registry_entry = _registry_entry()
    pages = (
        ExtractedPage(
            document_id="sample_manual",
            model_ids=("DC-TZ99",),
            page=1,
            text="첫 페이지",
            char_count=4,
        ),
        ExtractedPage(
            document_id="sample_manual",
            model_ids=("DC-TZ99",),
            page=3,
            text="셋째 페이지",
            char_count=5,
        ),
    )

    completed_pages = pdf_loader.complete_page_sequence(
        document=registry_entry,
        pages=pages,
        expected_page_count=3,
    )

    assert len(completed_pages) == 3
    assert completed_pages[1].page == 2
    assert completed_pages[1].text == ""
    assert completed_pages[1].char_count == 0


def _registry_entry() -> ManualDocumentRegistryEntry:
    return ManualDocumentRegistryEntry(
        document_id="sample_manual",
        title="Sample Manual",
        filename="sample.pdf",
        model_ids=("DC-TZ99",),
        language="ko",
        document_type="advanced_manual",
    )
