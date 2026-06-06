import sys
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.indexing.batch_extractor import ExtractionReport
from backend.app.indexing.fts_index import DEFAULT_FTS_INDEX_PATH
from backend.app.schemas.document import (
    ManualDocumentRegistryEntry,
    RegistryCatalog,
)
from backend.app.services.registry import RegistryValidationError, load_registry

DEFAULT_MANUALS_DIR: Final = Path("data/raw/manuals")
DEFAULT_PROCESSED_DIR: Final = Path("data/processed")
DEFAULT_REGISTRY_DIR: Final = Path("data/registry")
type IngestionCheckStatus = Literal["ok", "missing", "stale"]


class IngestionCheck(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    status: IngestionCheckStatus
    path: Path
    action: str = Field(min_length=1)


class NewPdfIngestionPlan(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_ids: tuple[str, ...]
    ready: bool
    checks: tuple[IngestionCheck, ...]
    viewer_smoke_paths: tuple[str, ...]
    next_commands: tuple[str, ...]


def build_new_pdf_ingestion_plan(
    *,
    catalog: RegistryCatalog,
    document_ids: Sequence[str],
    manuals_dir: Path = DEFAULT_MANUALS_DIR,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    index_path: Path = DEFAULT_FTS_INDEX_PATH,
) -> NewPdfIngestionPlan:
    documents = _select_documents(catalog=catalog, document_ids=document_ids)
    checks = tuple(
        check
        for document in documents
        for check in _document_checks(
            document=document,
            manuals_dir=manuals_dir,
            processed_dir=processed_dir,
        )
    ) + _shared_checks(
        documents=documents,
        processed_dir=processed_dir,
        index_path=index_path,
    )
    return NewPdfIngestionPlan(
        document_ids=tuple(document.document_id for document in documents),
        ready=all(check.status == "ok" for check in checks),
        checks=checks,
        viewer_smoke_paths=tuple(
            f"/api/viewer/{document.document_id}/pages/1" for document in documents
        ),
        next_commands=_next_commands(document_ids=tuple(document_ids)),
    )


def main() -> None:
    catalog = load_registry(DEFAULT_REGISTRY_DIR)
    document_ids = tuple(sys.argv[1:])
    plan = build_new_pdf_ingestion_plan(
        catalog=catalog,
        document_ids=document_ids,
    )
    _ = sys.stdout.write(plan.model_dump_json(indent=2) + "\n")


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


def _document_checks(
    *,
    document: ManualDocumentRegistryEntry,
    manuals_dir: Path,
    processed_dir: Path,
) -> tuple[IngestionCheck, ...]:
    return (
        _check(
            name="raw_pdf",
            path=manuals_dir / document.filename,
            action="place original PDF under data/raw/manuals",
        ),
        _check(
            name="processed_pages",
            path=processed_dir / "pages" / f"{document.document_id}.jsonl",
            action="run batch extraction for processed pages",
        ),
        _check(
            name="processed_chunks",
            path=processed_dir / "chunks" / f"{document.document_id}.jsonl",
            action="run batch extraction for processed chunks",
        ),
    )


def _shared_checks(
    *,
    documents: tuple[ManualDocumentRegistryEntry, ...],
    processed_dir: Path,
    index_path: Path,
) -> tuple[IngestionCheck, ...]:
    return (
        _check_extraction_report(
            path=processed_dir / "reports" / "extraction_report.json",
            document_ids=tuple(document.document_id for document in documents),
        ),
        _check(
            name="fts_index",
            path=index_path,
            action="rebuild SQLite FTS5 index",
        ),
    )


def _check_extraction_report(
    *,
    path: Path,
    document_ids: tuple[str, ...],
) -> IngestionCheck:
    if not path.is_file():
        return IngestionCheck(
            name="extraction_report",
            status="missing",
            path=path,
            action="write extraction report after batch extraction",
        )
    try:
        report = ExtractionReport.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError:
        return IngestionCheck(
            name="extraction_report",
            status="stale",
            path=path,
            action="rewrite extraction report with valid schema",
        )
    recorded_ids = {record.document_id for record in report.records}
    missing_record_ids = set(document_ids) - recorded_ids
    status: IngestionCheckStatus = "stale" if missing_record_ids else "ok"
    return IngestionCheck(
        name="extraction_report",
        status=status,
        path=path,
        action="rewrite extraction report after batch extraction",
    )


def _check(
    *,
    name: str,
    path: Path,
    action: str,
) -> IngestionCheck:
    status: IngestionCheckStatus = "ok" if path.is_file() else "missing"
    return IngestionCheck(name=name, status=status, path=path, action=action)


def _next_commands(*, document_ids: tuple[str, ...]) -> tuple[str, ...]:
    selected = " ".join(document_ids)
    extraction_command = (
        ".venv/bin/uv run python -m backend.app.indexing.batch_extractor"
    )
    if selected:
        extraction_command = f"{extraction_command} {selected}"
    return (
        extraction_command,
        ".venv/bin/uv run python -m backend.app.indexing.fts_index",
        ".venv/bin/uv run python -m backend.app.evaluation.search_eval",
        ".venv/bin/uv run pytest backend/tests/test_viewer_route.py",
    )


if __name__ == "__main__":
    main()
