from pathlib import Path

from backend.app.indexing.new_pdf_ingestion import (
    build_new_pdf_ingestion_plan,
)
from backend.app.schemas.document import (
    CameraModelRegistryEntry,
    ManualDocumentRegistryEntry,
    RegistryCatalog,
)


def test_build_new_pdf_ingestion_plan_reports_ready_document(
    tmp_path: Path,
) -> None:
    manuals_dir = tmp_path / "manuals"
    processed_dir = tmp_path / "processed"
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    manuals_dir.mkdir()
    (processed_dir / "pages").mkdir(parents=True)
    (processed_dir / "chunks").mkdir(parents=True)
    (processed_dir / "reports").mkdir(parents=True)
    index_path.parent.mkdir()
    _ = (manuals_dir / "sample.pdf").write_bytes(b"%PDF")
    _ = (processed_dir / "pages" / "sample_manual.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )
    _ = (processed_dir / "chunks" / "sample_manual.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )
    _ = (processed_dir / "reports" / "extraction_report.json").write_text(
        (
            '{"document_count":1,"records":[{"document_id":"sample_manual",'
            '"filename":"sample.pdf","model_ids":["DC-S9"],'
            '"loader":"opendataloader","page_count":1,"chunk_count":1,'
            '"char_count":1,"duration_seconds":0,"fallback_reason":null}]}\n'
        ),
        encoding="utf-8",
    )
    _ = index_path.write_bytes(b"sqlite")

    report = build_new_pdf_ingestion_plan(
        catalog=_catalog(),
        document_ids=("sample_manual",),
        manuals_dir=manuals_dir,
        processed_dir=processed_dir,
        index_path=index_path,
    )

    assert report.ready is True
    assert [check.status for check in report.checks] == ["ok"] * len(report.checks)
    assert report.viewer_smoke_paths == ("/api/viewer/sample_manual/pages/1",)


def test_build_new_pdf_ingestion_plan_rejects_stale_extraction_report(
    tmp_path: Path,
) -> None:
    manuals_dir = tmp_path / "manuals"
    processed_dir = tmp_path / "processed"
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    manuals_dir.mkdir()
    (processed_dir / "pages").mkdir(parents=True)
    (processed_dir / "chunks").mkdir(parents=True)
    (processed_dir / "reports").mkdir(parents=True)
    index_path.parent.mkdir()
    _ = (manuals_dir / "sample.pdf").write_bytes(b"%PDF")
    _ = (processed_dir / "pages" / "sample_manual.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )
    _ = (processed_dir / "chunks" / "sample_manual.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )
    _ = (processed_dir / "reports" / "extraction_report.json").write_text(
        '{"document_count":0,"records":[]}\n',
        encoding="utf-8",
    )
    _ = index_path.write_bytes(b"sqlite")

    report = build_new_pdf_ingestion_plan(
        catalog=_catalog(),
        document_ids=("sample_manual",),
        manuals_dir=manuals_dir,
        processed_dir=processed_dir,
        index_path=index_path,
    )

    report_check = next(
        check for check in report.checks if check.name == "extraction_report"
    )
    assert report.ready is False
    assert report_check.status == "stale"


def test_build_new_pdf_ingestion_plan_reports_missing_artifacts(
    tmp_path: Path,
) -> None:
    manuals_dir = tmp_path / "manuals"
    processed_dir = tmp_path / "processed"
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    manuals_dir.mkdir()

    report = build_new_pdf_ingestion_plan(
        catalog=_catalog(),
        document_ids=("sample_manual",),
        manuals_dir=manuals_dir,
        processed_dir=processed_dir,
        index_path=index_path,
    )

    assert report.ready is False
    assert [check.name for check in report.checks if check.status == "missing"] == [
        "raw_pdf",
        "processed_pages",
        "processed_chunks",
        "extraction_report",
        "fts_index",
    ]


def _catalog() -> RegistryCatalog:
    return RegistryCatalog(
        documents=(
            ManualDocumentRegistryEntry(
                document_id="sample_manual",
                title="Sample Manual",
                filename="sample.pdf",
                model_ids=("DC-S9",),
                language="ko",
                document_type="full_manual",
            ),
        ),
        models=(
            CameraModelRegistryEntry(
                model_id="DC-S9",
                display_name="LUMIX S9",
                product_line="LUMIX S",
            ),
        ),
    )
