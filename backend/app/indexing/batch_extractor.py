import sys
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.core.settings import get_settings
from backend.app.indexing.chunker import write_document_chunks_jsonl
from backend.app.indexing.pdf_extractor import write_document_pages_jsonl
from backend.app.indexing.pdf_loader import (
    PdfLoaderName,
    extract_document_pages_primary,
)
from backend.app.schemas.document import ManualDocumentRegistryEntry, RegistryCatalog
from backend.app.services.brand_data_paths import brand_data_paths
from backend.app.services.brand_registry import resolve_brand
from backend.app.services.registry import (
    RegistryValidationError,
    load_registry,
    validate_manual_files,
)

DEFAULT_BRAND_ID: Final = "panasonic_lumix"
BRAND_ID_FLAG: Final = "--brand-id"


class BatchExtractionArgumentError(ValueError):
    @classmethod
    def missing_brand_id(cls) -> "BatchExtractionArgumentError":
        return cls(f"{BRAND_ID_FLAG} requires a value")


class BatchExtractionArgs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    brand_id: str
    document_ids: tuple[str, ...]


class ExtractionRecord(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_id: str
    filename: str
    model_ids: tuple[str, ...]
    loader: PdfLoaderName
    page_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    char_count: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    fallback_reason: str | None = None


class ExtractionReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_count: int = Field(ge=0)
    records: tuple[ExtractionRecord, ...]


def run_batch_extraction(
    *,
    catalog: RegistryCatalog,
    manuals_dir: Path,
    output_root: Path,
    document_ids: Sequence[str] = (),
) -> ExtractionReport:
    documents = _select_documents(catalog=catalog, document_ids=document_ids)
    validate_manual_files(
        catalog=RegistryCatalog(documents=documents, models=catalog.models),
        manuals_dir=manuals_dir,
    )
    records = tuple(
        _extract_one(
            document=document,
            manuals_dir=manuals_dir,
            output_root=output_root,
        )
        for document in documents
    )
    report = _extraction_report(
        records=records,
        selected_document_ids=tuple(document_ids),
        report_path=output_root / "reports" / "extraction_report.json",
    )
    _ = write_extraction_report(report=report, output_dir=output_root / "reports")
    return report


def write_extraction_report(
    *,
    report: ExtractionReport,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "extraction_report.json"
    _ = output_path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _extraction_report(
    *,
    records: tuple[ExtractionRecord, ...],
    selected_document_ids: tuple[str, ...],
    report_path: Path,
) -> ExtractionReport:
    if not selected_document_ids:
        return ExtractionReport(document_count=len(records), records=records)
    existing_report = _load_existing_report(report_path=report_path)
    if existing_report is None:
        return ExtractionReport(document_count=len(records), records=records)
    selected_ids = set(selected_document_ids)
    retained_records = tuple(
        record
        for record in existing_report.records
        if record.document_id not in selected_ids
    )
    merged_records = retained_records + records
    return ExtractionReport(document_count=len(merged_records), records=merged_records)


def _load_existing_report(*, report_path: Path) -> ExtractionReport | None:
    try:
        raw_json = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        return ExtractionReport.model_validate_json(raw_json)
    except ValidationError:
        return None


def main() -> None:
    try:
        args = parse_batch_extraction_args(tuple(sys.argv[1:]))
    except BatchExtractionArgumentError as error:
        raise SystemExit(str(error)) from error
    brand = resolve_brand(settings=get_settings(), brand_id=args.brand_id)
    paths = brand_data_paths(brand.data_dir)
    catalog = load_registry(paths.registry_dir)
    report = run_batch_extraction(
        catalog=catalog,
        manuals_dir=paths.manuals_dir,
        output_root=paths.root / "processed",
        document_ids=args.document_ids,
    )
    _ = sys.stdout.write(f"extracted {report.document_count} documents\n")


def parse_batch_extraction_args(argv: Sequence[str]) -> BatchExtractionArgs:
    brand_id = DEFAULT_BRAND_ID
    document_ids: list[str] = []
    pending_brand_id = False
    for value in argv:
        if pending_brand_id:
            if not value or value.startswith("--"):
                raise BatchExtractionArgumentError.missing_brand_id()
            brand_id = value
            pending_brand_id = False
            continue
        if value == BRAND_ID_FLAG:
            pending_brand_id = True
            continue
        document_ids.append(value)
    if pending_brand_id:
        raise BatchExtractionArgumentError.missing_brand_id()
    return BatchExtractionArgs(
        brand_id=brand_id,
        document_ids=tuple(document_ids),
    )


def _select_documents(
    *,
    catalog: RegistryCatalog,
    document_ids: Sequence[str],
) -> tuple[ManualDocumentRegistryEntry, ...]:
    if not document_ids:
        return catalog.documents
    selected_ids = set(document_ids)
    documents = tuple(
        document
        for document in catalog.documents
        if document.document_id in selected_ids
    )
    missing_ids = selected_ids - {document.document_id for document in documents}
    if missing_ids:
        raise RegistryValidationError(
            [f"unknown document_id: {document_id}" for document_id in missing_ids],
        )
    return documents


def _extract_one(
    *,
    document: ManualDocumentRegistryEntry,
    manuals_dir: Path,
    output_root: Path,
) -> ExtractionRecord:
    started_at = perf_counter()
    result = extract_document_pages_primary(
        document=document,
        pdf_path=manuals_dir / document.filename,
    )
    _ = write_document_pages_jsonl(
        pages=result.pages,
        output_dir=output_root / "pages",
    )
    _ = write_document_chunks_jsonl(
        chunks=result.chunks,
        document_id=document.document_id,
        output_dir=output_root / "chunks",
    )
    return ExtractionRecord(
        document_id=document.document_id,
        filename=document.filename,
        model_ids=document.model_ids,
        loader=result.loader,
        page_count=len(result.pages),
        chunk_count=len(result.chunks),
        char_count=sum(page.char_count for page in result.pages),
        duration_seconds=perf_counter() - started_at,
        fallback_reason=result.fallback_reason,
    )


if __name__ == "__main__":
    main()
