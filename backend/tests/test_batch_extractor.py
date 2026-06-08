from pathlib import Path

import pytest
from backend.app.indexing import batch_extractor
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.pdf_extractor import ExtractedPage
from backend.app.indexing.pdf_loader import PdfLoaderName, PdfLoaderResult
from backend.app.schemas.document import (
    CameraModelRegistryEntry,
    ManualDocumentRegistryEntry,
    RegistryCatalog,
)


def test_run_batch_extraction_writes_artifacts_for_selected_documents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    catalog = _catalog()
    manuals_dir = tmp_path / "manuals"
    manuals_dir.mkdir()
    _ = (manuals_dir / "sample-a.pdf").write_bytes(b"%PDF")
    output_root = tmp_path / "processed"
    result = _loader_result(document_id="sample_a")

    def fake_extract_document_pages_primary(
        *,
        document: ManualDocumentRegistryEntry,
        pdf_path: Path,
    ) -> PdfLoaderResult:
        assert document.document_id == "sample_a"
        assert pdf_path == manuals_dir / "sample-a.pdf"
        return result

    monkeypatch.setattr(
        batch_extractor,
        "extract_document_pages_primary",
        fake_extract_document_pages_primary,
    )

    report = batch_extractor.run_batch_extraction(
        catalog=catalog,
        manuals_dir=manuals_dir,
        output_root=output_root,
        document_ids=("sample_a",),
    )

    assert report.document_count == 1
    assert report.records[0].document_id == "sample_a"
    assert report.records[0].loader == "opendataloader"
    assert (output_root / "pages" / "sample_a.jsonl").is_file()
    assert (output_root / "chunks" / "sample_a.jsonl").is_file()
    assert (output_root / "reports" / "extraction_report.json").is_file()
    assert not (output_root / "pages" / "sample_b.jsonl").exists()


def test_run_batch_extraction_report_records_fallback_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    catalog = _catalog()
    manuals_dir = tmp_path / "manuals"
    manuals_dir.mkdir()
    _ = (manuals_dir / "sample-a.pdf").write_bytes(b"%PDF")
    output_root = tmp_path / "processed"
    result = _loader_result(document_id="sample_a", fallback_reason="cli not found")

    def fake_extract_document_pages_primary(
        *,
        document: ManualDocumentRegistryEntry,
        pdf_path: Path,
    ) -> PdfLoaderResult:
        assert document.document_id == "sample_a"
        assert pdf_path == manuals_dir / "sample-a.pdf"
        return result

    monkeypatch.setattr(
        batch_extractor,
        "extract_document_pages_primary",
        fake_extract_document_pages_primary,
    )

    report = batch_extractor.run_batch_extraction(
        catalog=catalog,
        manuals_dir=manuals_dir,
        output_root=output_root,
        document_ids=("sample_a",),
    )

    record = report.records[0]
    assert record.loader == "pypdf"
    assert record.fallback_reason == "cli not found"
    assert record.page_count == 1
    assert record.chunk_count == 1
    assert record.char_count == 4


def test_run_batch_extraction_merges_selected_document_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    catalog = _catalog()
    manuals_dir = tmp_path / "manuals"
    manuals_dir.mkdir()
    _ = (manuals_dir / "sample-a.pdf").write_bytes(b"%PDF")
    output_root = tmp_path / "processed"
    _ = batch_extractor.write_extraction_report(
        report=batch_extractor.ExtractionReport(
            document_count=1,
            records=(
                batch_extractor.ExtractionRecord(
                    document_id="sample_b",
                    filename="sample-b.pdf",
                    model_ids=("DC-TZ99",),
                    loader="opendataloader",
                    page_count=2,
                    chunk_count=2,
                    char_count=8,
                    duration_seconds=0,
                    fallback_reason=None,
                ),
            ),
        ),
        output_dir=output_root / "reports",
    )
    result = _loader_result(document_id="sample_a")

    def fake_extract_document_pages_primary(
        *,
        document: ManualDocumentRegistryEntry,
        pdf_path: Path,
    ) -> PdfLoaderResult:
        assert document.document_id == "sample_a"
        assert pdf_path == manuals_dir / "sample-a.pdf"
        return result

    monkeypatch.setattr(
        batch_extractor,
        "extract_document_pages_primary",
        fake_extract_document_pages_primary,
    )

    report = batch_extractor.run_batch_extraction(
        catalog=catalog,
        manuals_dir=manuals_dir,
        output_root=output_root,
        document_ids=("sample_a",),
    )

    assert report.document_count == 2
    assert tuple(record.document_id for record in report.records) == (
        "sample_b",
        "sample_a",
    )


def test_batch_extractor_main_accepts_document_id_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_document_ids: tuple[str, ...] = ()

    def fake_load_registry(registry_dir: Path) -> RegistryCatalog:
        assert registry_dir == Path("data/brands/panasonic_lumix/registry")
        return _catalog()

    def fake_run_batch_extraction(
        *,
        catalog: RegistryCatalog,
        manuals_dir: Path,
        output_root: Path,
        document_ids: tuple[str, ...] = (),
    ) -> batch_extractor.ExtractionReport:
        nonlocal captured_document_ids
        assert catalog == _catalog()
        assert manuals_dir == Path("data/brands/panasonic_lumix/raw/manuals")
        assert output_root == Path("data/brands/panasonic_lumix/processed")
        captured_document_ids = document_ids
        return batch_extractor.ExtractionReport(document_count=1, records=())

    monkeypatch.setattr(batch_extractor, "load_registry", fake_load_registry)
    monkeypatch.setattr(
        batch_extractor,
        "run_batch_extraction",
        fake_run_batch_extraction,
    )
    monkeypatch.setattr("sys.argv", ["batch_extractor", "sample_a"])

    batch_extractor.main()

    assert captured_document_ids == ("sample_a",)


def test_parse_batch_extraction_args_reads_brand_id() -> None:
    args = batch_extractor.parse_batch_extraction_args(
        ("--brand-id", "ricoh", "sample_a"),
    )

    assert args.brand_id == "ricoh"
    assert args.document_ids == ("sample_a",)


def _loader_result(
    *,
    document_id: str,
    fallback_reason: str | None = None,
) -> PdfLoaderResult:
    loader: PdfLoaderName = "pypdf" if fallback_reason else "opendataloader"
    return PdfLoaderResult(
        loader=loader,
        pages=(
            ExtractedPage(
                document_id=document_id,
                model_ids=("DC-TZ99",),
                page=1,
                text="본문",
                char_count=4,
            ),
        ),
        chunks=(
            ExtractedChunk(
                chunk_id=f"{document_id}:page:1",
                document_id=document_id,
                model_ids=("DC-TZ99",),
                page_start=1,
                page_end=1,
                section_title=None,
                chunk_type="page",
                content="본문",
                char_count=4,
                source_hash="0" * 64,
            ),
        ),
        chunk_count=1,
        fallback_reason=fallback_reason,
    )


def _catalog() -> RegistryCatalog:
    return RegistryCatalog(
        documents=(
            ManualDocumentRegistryEntry(
                document_id="sample_a",
                title="Sample A",
                filename="sample-a.pdf",
                model_ids=("DC-TZ99",),
                language="ko",
                document_type="advanced_manual",
            ),
            ManualDocumentRegistryEntry(
                document_id="sample_b",
                title="Sample B",
                filename="sample-b.pdf",
                model_ids=("DC-TZ99",),
                language="ko",
                document_type="advanced_manual",
            ),
        ),
        models=(
            CameraModelRegistryEntry(
                model_id="DC-TZ99",
                display_name="LUMIX TZ99",
                product_line="LUMIX TZ",
            ),
        ),
    )
