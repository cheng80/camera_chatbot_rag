from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.app.indexing.chunker import ExtractedChunk, build_page_chunks
from backend.app.indexing.opendataloader_adapter import (
    adapt_opendataloader_json_to_chunks,
    adapt_opendataloader_json_to_pages,
)
from backend.app.indexing.opendataloader_runner import (
    FALLBACK_ALLOWED_KINDS,
    OpenDataLoaderExtractionError,
    resolve_opendataloader_cli,
    run_opendataloader,
)
from backend.app.indexing.pdf_extractor import (
    ExtractedPage,
    PdfExtractionError,
    extract_document_pages,
    write_document_pages_jsonl,
)
from backend.app.schemas.document import ManualDocumentRegistryEntry

PdfLoaderName = Literal["opendataloader", "pypdf"]


class PdfLoaderResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    loader: PdfLoaderName
    pages: tuple[ExtractedPage, ...]
    chunks: tuple[ExtractedChunk, ...] = ()
    chunk_count: int = Field(ge=0)
    fallback_reason: str | None = None


class PdfLoaderMetadata(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_id: str
    loader: PdfLoaderName
    page_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    fallback_reason: str | None = None


def extract_document_pages_primary(
    *,
    document: ManualDocumentRegistryEntry,
    pdf_path: Path,
) -> PdfLoaderResult:
    try:
        pages, chunks = _extract_with_opendataloader(
            document=document,
            pdf_path=pdf_path,
        )
    except OpenDataLoaderExtractionError as error:
        if error.kind not in FALLBACK_ALLOWED_KINDS:
            raise
        fallback_pages = extract_document_pages(document=document, pdf_path=pdf_path)
        fallback_chunks = build_page_chunks(fallback_pages)
        return PdfLoaderResult(
            loader="pypdf",
            pages=fallback_pages,
            chunks=fallback_chunks,
            chunk_count=len(fallback_chunks),
            fallback_reason=error.reason,
        )

    return PdfLoaderResult(
        loader="opendataloader",
        pages=pages,
        chunks=chunks,
        chunk_count=len(chunks),
        fallback_reason=None,
    )


def extract_and_write_document_pages_primary(
    *,
    document: ManualDocumentRegistryEntry,
    manuals_dir: Path,
    output_dir: Path,
) -> Path:
    result = extract_document_pages_primary(
        document=document,
        pdf_path=manuals_dir / document.filename,
    )
    output_path = write_document_pages_jsonl(pages=result.pages, output_dir=output_dir)
    _ = write_pdf_loader_metadata(result=result, output_dir=output_dir)
    return output_path


def write_pdf_loader_metadata(
    *,
    result: PdfLoaderResult,
    output_dir: Path,
) -> Path:
    metadata = PdfLoaderMetadata(
        document_id=result.pages[0].document_id if result.pages else "",
        loader=result.loader,
        page_count=len(result.pages),
        chunk_count=result.chunk_count,
        fallback_reason=result.fallback_reason,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{metadata.document_id}.loader.json"
    _ = output_path.write_text(metadata.model_dump_json() + "\n", encoding="utf-8")
    return output_path


def _extract_with_opendataloader(
    *,
    document: ManualDocumentRegistryEntry,
    pdf_path: Path,
) -> tuple[tuple[ExtractedPage, ...], tuple[ExtractedChunk, ...]]:
    expected_page_count = _read_pdf_page_count(pdf_path)
    cli_path = resolve_opendataloader_cli()
    with TemporaryDirectory(prefix="lumix-opendl-") as temp_dir:
        output_dir = Path(temp_dir)
        run_opendataloader(cli_path=cli_path, pdf_path=pdf_path, output_dir=output_dir)
        json_path = output_dir / f"{pdf_path.stem}.json"
        if not json_path.is_file():
            raise OpenDataLoaderExtractionError.missing_json()
        pages = adapt_opendataloader_json_to_pages(
            document=document,
            json_path=json_path,
        )
        chunks = adapt_opendataloader_json_to_chunks(
            document=document,
            json_path=json_path,
        )
    completed_pages = complete_page_sequence(
        document=document,
        pages=pages,
        expected_page_count=expected_page_count,
    )
    _validate_opendataloader_pages(
        pages=completed_pages,
        expected_page_count=expected_page_count,
    )
    return completed_pages, chunks


def _read_pdf_page_count(pdf_path: Path) -> int:
    try:
        return len(PdfReader(pdf_path).pages)
    except FileNotFoundError as error:
        raise PdfExtractionError.missing_file(pdf_path) from error
    except PdfReadError as error:
        raise PdfExtractionError.unreadable_file(pdf_path) from error


def complete_page_sequence(
    *,
    document: ManualDocumentRegistryEntry,
    pages: tuple[ExtractedPage, ...],
    expected_page_count: int,
) -> tuple[ExtractedPage, ...]:
    if not pages:
        return ()
    max_extracted_page = max(page.page for page in pages)
    if max_extracted_page > expected_page_count:
        raise OpenDataLoaderExtractionError.page_count_mismatch(
            extracted=max_extracted_page,
            expected=expected_page_count,
        )
    pages_by_number = {page.page: page for page in pages}
    return tuple(
        pages_by_number.get(page_number)
        or ExtractedPage(
            document_id=document.document_id,
            model_ids=document.model_ids,
            page=page_number,
            text="",
            char_count=0,
        )
        for page_number in range(1, expected_page_count + 1)
    )


def _validate_opendataloader_pages(
    *,
    pages: tuple[ExtractedPage, ...],
    expected_page_count: int,
) -> None:
    if not pages:
        raise OpenDataLoaderExtractionError.no_pages()
    if len(pages) != expected_page_count:
        raise OpenDataLoaderExtractionError.page_count_mismatch(
            extracted=len(pages),
            expected=expected_page_count,
        )
    if sum(page.char_count for page in pages) == 0:
        raise OpenDataLoaderExtractionError.empty_pages()
