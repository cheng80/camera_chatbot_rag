import re
from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.pdf_extractor import ExtractedPage
from backend.app.services.registry import RegistryValidationError, load_registry

DEFAULT_REGISTRY_DIR: Final = Path("data/registry")
DEFAULT_PAGES_DIR: Final = Path("data/processed/pages")
SAFE_DOCUMENT_ID_RE: Final = re.compile(r"^[a-z0-9_]+$")
PAGES_ADAPTER: Final[TypeAdapter[tuple[ExtractedPage, ...]]] = TypeAdapter(
    tuple[ExtractedPage, ...],
)
type PageFileSignature = tuple[int, int]

type SourceReferenceErrorCode = Literal[
    "document_model_mismatch",
    "model_not_found",
    "document_not_found",
    "unsafe_document_id",
    "page_out_of_range",
    "processed_pages_missing",
    "registry_invalid",
]


class SourceReferenceCandidate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    page: int = Field(ge=1)


class SourceReferenceValidationError(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    code: SourceReferenceErrorCode
    message: str = Field(min_length=1)


class SourceReferenceValidationResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    model_id: str
    page: int
    valid: bool
    viewer_url: str | None
    errors: tuple[SourceReferenceValidationError, ...] = Field(default_factory=tuple)


def validate_source_reference(
    reference: SourceReferenceCandidate,
    *,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    pages_dir: Path = DEFAULT_PAGES_DIR,
) -> SourceReferenceValidationResult:
    if not _is_safe_document_id(reference.document_id):
        return _invalid_result(
            reference=reference,
            errors=(
                SourceReferenceValidationError(
                    code="unsafe_document_id",
                    message=f"unsafe document_id: {reference.document_id}",
                ),
            ),
        )

    try:
        catalog = load_registry(registry_dir)
    except RegistryValidationError as error:
        return _invalid_result(
            reference=reference,
            errors=(
                SourceReferenceValidationError(
                    code="registry_invalid",
                    message=str(error),
                ),
            ),
        )

    document = next(
        (
            catalog_document
            for catalog_document in catalog.documents
            if catalog_document.document_id == reference.document_id
        ),
        None,
    )
    known_model_ids = {model.model_id for model in catalog.models}
    errors: list[SourceReferenceValidationError] = []

    if document is None:
        errors.append(
            SourceReferenceValidationError(
                code="document_not_found",
                message=f"unknown document_id: {reference.document_id}",
            ),
        )
    if reference.model_id not in known_model_ids:
        errors.append(
            SourceReferenceValidationError(
                code="model_not_found",
                message=f"unknown model_id: {reference.model_id}",
            ),
        )
    if document is not None and reference.model_id not in document.model_ids:
        errors.append(
            SourceReferenceValidationError(
                code="document_model_mismatch",
                message=(
                    f"{reference.document_id} does not include "
                    f"{reference.model_id}"
                ),
            ),
        )

    if document is not None:
        page_errors = _page_errors(reference=reference, pages_dir=pages_dir)
        errors.extend(page_errors)
    if errors:
        return _invalid_result(reference=reference, errors=tuple(errors))
    return SourceReferenceValidationResult(
        document_id=reference.document_id,
        model_id=reference.model_id,
        page=reference.page,
        valid=True,
        viewer_url=_viewer_url(reference),
        errors=(),
    )


def _page_errors(
    *,
    reference: SourceReferenceCandidate,
    pages_dir: Path,
) -> tuple[SourceReferenceValidationError, ...]:
    pages_path = pages_dir / f"{reference.document_id}.jsonl"
    if not pages_path.is_file():
        return (
            SourceReferenceValidationError(
                code="processed_pages_missing",
                message=f"missing processed pages: {pages_path}",
            ),
        )
    pages = _load_document_pages(
        path=pages_path,
        signature=_page_file_signature(pages_path),
    )
    known_pages = {page.page for page in pages}
    if reference.page in known_pages:
        return ()
    min_page = min(known_pages, default=0)
    max_page = max(known_pages, default=0)
    return (
        SourceReferenceValidationError(
            code="page_out_of_range",
            message=(
                f"page {reference.page} is outside processed page range "
                f"{min_page}-{max_page} for {reference.document_id}"
            ),
        ),
    )


@lru_cache(maxsize=128)
def _load_document_pages(
    *,
    path: Path,
    signature: PageFileSignature,
) -> tuple[ExtractedPage, ...]:
    _ = signature
    content = f"[{','.join(path.read_text(encoding='utf-8').splitlines())}]"
    return PAGES_ADAPTER.validate_json(content)


def _page_file_signature(path: Path) -> PageFileSignature:
    stat_result = path.stat()
    return (stat_result.st_mtime_ns, stat_result.st_size)


def _is_safe_document_id(document_id: str) -> bool:
    return SAFE_DOCUMENT_ID_RE.fullmatch(document_id) is not None


def _invalid_result(
    *,
    reference: SourceReferenceCandidate,
    errors: tuple[SourceReferenceValidationError, ...],
) -> SourceReferenceValidationResult:
    return SourceReferenceValidationResult(
        document_id=reference.document_id,
        model_id=reference.model_id,
        page=reference.page,
        valid=False,
        viewer_url=None,
        errors=errors,
    )


def _viewer_url(reference: SourceReferenceCandidate) -> str:
    return f"/api/viewer/{reference.document_id}/pages/{reference.page}"
