from pathlib import Path

import pytest
from backend.app.indexing import ingest_new_pdf
from backend.app.indexing.batch_extractor import ExtractionReport
from backend.app.indexing.fts_index import FtsIndexReport
from backend.app.schemas.document import RegistryCatalog
from backend.tests.registry_fixtures import empty_catalog, write_registry


def test_run_ingest_new_pdf_registers_and_runs_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "registry"
    manuals_dir = tmp_path / "manuals"
    processed_dir = tmp_path / "processed"
    chunks_dir = processed_dir / "chunks"
    index_path = tmp_path / "index.sqlite3"
    write_registry(registry_dir=registry_dir, catalog=empty_catalog())
    manuals_dir.mkdir()
    pdf_path = manuals_dir / "DMC-G7.pdf"
    _ = pdf_path.write_bytes(b"%PDF")
    captured_document_ids: tuple[str, ...] = ()

    def fake_read_first_pages_text(*, pdf_path: Path, page_limit: int) -> str:
        assert page_limit == 3
        assert pdf_path.name == "DMC-G7.pdf"
        return "기본 사용 설명서 모델 번호 DMC-G7K/DMC-G7"

    def fake_run_batch_extraction(
        *,
        catalog: RegistryCatalog,
        manuals_dir: Path,
        output_root: Path,
        document_ids: tuple[str, ...] = (),
    ) -> ExtractionReport:
        nonlocal captured_document_ids
        _ = (catalog, manuals_dir, output_root)
        captured_document_ids = document_ids
        return ExtractionReport(document_count=1, records=())

    monkeypatch.setattr(
        ingest_new_pdf,
        "read_first_pages_text",
        fake_read_first_pages_text,
    )
    monkeypatch.setattr(
        ingest_new_pdf,
        "run_batch_extraction",
        fake_run_batch_extraction,
    )
    def fake_build_fts_index(
        *,
        chunks_dir: Path,
        index_path: Path,
    ) -> FtsIndexReport:
        _ = chunks_dir
        return FtsIndexReport(
            document_count=1,
            chunk_count=1,
            index_path=index_path,
        )

    def fake_run_search_eval(**kwargs: Path) -> None:
        _ = kwargs

    def fake_write_search_eval_report(**kwargs: object) -> None:
        _ = kwargs

    monkeypatch.setattr(
        ingest_new_pdf,
        "build_fts_index",
        fake_build_fts_index,
    )
    monkeypatch.setattr(ingest_new_pdf, "run_search_eval", fake_run_search_eval)
    monkeypatch.setattr(
        ingest_new_pdf,
        "write_search_eval_report",
        fake_write_search_eval_report,
    )

    result = ingest_new_pdf.run_ingest_new_pdf(
        pdf_path=pdf_path,
        paths=ingest_new_pdf.NewPdfIngestPaths(
            registry_dir=registry_dir,
            manuals_dir=manuals_dir,
            processed_dir=processed_dir,
            chunks_dir=chunks_dir,
            index_path=index_path,
        ),
    )

    assert result.registration_status == "auto_registerable"
    assert result.document_id == "dmc_g7_kor"
    assert captured_document_ids == ("dmc_g7_kor",)
