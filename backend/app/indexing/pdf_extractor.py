from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, override

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.app.schemas.document import ManualDocumentRegistryEntry


class ExtractedPage(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_id: str
    model_ids: tuple[str, ...]
    page: int = Field(ge=1)
    text: str
    char_count: int = Field(ge=0)


class PdfExtractionError(ValueError):
    @classmethod
    def missing_file(cls, path: Path) -> "PdfExtractionError":
        return cls(kind="missing_file", path=path)

    @classmethod
    def unreadable_file(cls, path: Path) -> "PdfExtractionError":
        return cls(kind="unreadable_file", path=path)

    @classmethod
    def empty_result(cls) -> "PdfExtractionError":
        return cls(kind="empty_result", path=None)

    def __init__(self, *, kind: str, path: Path | None) -> None:
        self.kind: str = kind
        self.path: Path | None = path
        super().__init__(str(self))

    @override
    def __str__(self) -> str:
        match self.kind:
            case "missing_file":
                return f"missing PDF file: {self.path}"
            case "unreadable_file":
                return f"unreadable PDF file: {self.path}"
            case "empty_result":
                return "cannot write empty page extraction result"
            case _:
                return "unknown PDF extraction error"


def extract_document_pages(
    *,
    document: ManualDocumentRegistryEntry,
    pdf_path: Path,
) -> tuple[ExtractedPage, ...]:
    try:
        reader = PdfReader(pdf_path)
    except FileNotFoundError as error:
        raise PdfExtractionError.missing_file(pdf_path) from error
    except PdfReadError as error:
        raise PdfExtractionError.unreadable_file(pdf_path) from error

    return tuple(
        ExtractedPage(
            document_id=document.document_id,
            model_ids=document.model_ids,
            page=page_index + 1,
            text=page_text,
            char_count=len(page_text),
        )
        for page_index, page_text in enumerate(_extract_page_texts(reader))
    )


def write_document_pages_jsonl(
    *,
    pages: Sequence[ExtractedPage],
    output_dir: Path,
) -> Path:
    if not pages:
        raise PdfExtractionError.empty_result()

    document_id = pages[0].document_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{document_id}.jsonl"
    lines = [page.model_dump_json() for page in pages]
    _ = output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def extract_and_write_document_pages(
    *,
    document: ManualDocumentRegistryEntry,
    manuals_dir: Path,
    output_dir: Path,
) -> Path:
    pages = extract_document_pages(
        document=document,
        pdf_path=manuals_dir / document.filename,
    )
    return write_document_pages_jsonl(pages=pages, output_dir=output_dir)


def _extract_page_texts(reader: PdfReader) -> tuple[str, ...]:
    page_texts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        page_texts.append(text.strip())
    return tuple(page_texts)
