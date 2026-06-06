import sys
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict

from backend.app.evaluation.search_eval import (
    DEFAULT_CASES_PATH,
    DEFAULT_REPORT_PATH,
    run_search_eval,
    write_search_eval_report,
)
from backend.app.indexing.batch_extractor import run_batch_extraction
from backend.app.indexing.fts_index import (
    DEFAULT_CHUNKS_DIR,
    DEFAULT_FTS_INDEX_PATH,
    build_fts_index,
)
from backend.app.indexing.new_pdf_auto_registration import (
    append_auto_registration,
    plan_pdf_auto_registration,
    read_first_pages_text,
)
from backend.app.indexing.new_pdf_ingestion import (
    DEFAULT_MANUALS_DIR,
    DEFAULT_PROCESSED_DIR,
    DEFAULT_REGISTRY_DIR,
    build_new_pdf_ingestion_plan,
)
from backend.app.services.registry import load_registry

ARG_COUNT: Final = 2
USAGE_MESSAGE: Final = "usage: python -m backend.app.indexing.ingest_new_pdf PDF"


class IngestNewPdfResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    registration_status: str
    document_id: str
    ingestion_ready: bool


class NewPdfIngestPaths(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    registry_dir: Path = DEFAULT_REGISTRY_DIR
    manuals_dir: Path = DEFAULT_MANUALS_DIR
    processed_dir: Path = DEFAULT_PROCESSED_DIR
    chunks_dir: Path = DEFAULT_CHUNKS_DIR
    index_path: Path = DEFAULT_FTS_INDEX_PATH


class NewPdfIngestBlockedError(ValueError):
    def __init__(self, reasons: tuple[str, ...]) -> None:
        self.reasons: tuple[str, ...] = reasons
        super().__init__("; ".join(reasons))


def run_ingest_new_pdf(
    *,
    pdf_path: Path,
    paths: NewPdfIngestPaths | None = None,
) -> IngestNewPdfResult:
    resolved_paths = paths or NewPdfIngestPaths()
    catalog = load_registry(resolved_paths.registry_dir)
    first_pages_text = read_first_pages_text(pdf_path=pdf_path, page_limit=3)
    registration = plan_pdf_auto_registration(
        pdf_path=pdf_path,
        catalog=catalog,
        manuals_dir=resolved_paths.manuals_dir,
        first_pages_text=first_pages_text,
    )
    if registration.status == "blocked" or registration.document is None:
        raise NewPdfIngestBlockedError(registration.block_reasons)
    append_auto_registration(
        plan=registration,
        registry_dir=resolved_paths.registry_dir,
    )
    updated_catalog = load_registry(resolved_paths.registry_dir)
    document_id = registration.document.document_id
    _ = run_batch_extraction(
        catalog=updated_catalog,
        manuals_dir=resolved_paths.manuals_dir,
        output_root=resolved_paths.processed_dir,
        document_ids=(document_id,),
    )
    _ = build_fts_index(
        chunks_dir=resolved_paths.chunks_dir,
        index_path=resolved_paths.index_path,
    )
    report = run_search_eval(
        cases_path=DEFAULT_CASES_PATH,
        index_path=resolved_paths.index_path,
        registry_dir=resolved_paths.registry_dir,
        pages_dir=resolved_paths.processed_dir / "pages",
    )
    _ = write_search_eval_report(report=report, path=DEFAULT_REPORT_PATH)
    plan = build_new_pdf_ingestion_plan(
        catalog=load_registry(resolved_paths.registry_dir),
        document_ids=(document_id,),
        manuals_dir=resolved_paths.manuals_dir,
        processed_dir=resolved_paths.processed_dir,
        index_path=resolved_paths.index_path,
    )
    return IngestNewPdfResult(
        registration_status=registration.status,
        document_id=document_id,
        ingestion_ready=plan.ready,
    )


def main() -> None:
    if len(sys.argv) != ARG_COUNT:
        raise SystemExit(USAGE_MESSAGE)
    try:
        result = run_ingest_new_pdf(pdf_path=Path(sys.argv[1]))
    except NewPdfIngestBlockedError as error:
        message = f"blocked: {error}"
        raise SystemExit(message) from error
    _ = sys.stdout.write(result.model_dump_json(indent=2) + "\n")


if __name__ == "__main__":
    main()
