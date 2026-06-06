from collections.abc import Sequence
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter, ValidationError

from backend.app.schemas.document import (
    CameraModel,
    CameraModelRegistryEntry,
    DocumentSummary,
    ManualDocumentRegistryEntry,
    RegistryCatalog,
)

DOCUMENTS_FILE: Final = "documents.json"
MODELS_FILE: Final = "models.json"

DOCUMENTS_ADAPTER: Final = TypeAdapter(tuple[ManualDocumentRegistryEntry, ...])
MODELS_ADAPTER: Final = TypeAdapter(tuple[CameraModelRegistryEntry, ...])


class RegistryValidationError(ValueError):
    def __init__(self, errors: Sequence[str]) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        message = "; ".join(self.errors)
        super().__init__(message)


def load_registry(registry_dir: Path) -> RegistryCatalog:
    documents = _load_documents(registry_dir / DOCUMENTS_FILE)
    models = _load_models(registry_dir / MODELS_FILE)
    _validate_catalog(documents=documents, models=models)
    return RegistryCatalog(documents=documents, models=models)


def validate_manual_files(
    *,
    catalog: RegistryCatalog,
    manuals_dir: Path,
) -> None:
    missing_files = tuple(
        document.filename
        for document in catalog.documents
        if not (manuals_dir / document.filename).is_file()
    )
    if missing_files:
        raise RegistryValidationError(
            [f"missing PDF file: {filename}" for filename in missing_files],
        )


def summarize_documents(catalog: RegistryCatalog) -> list[DocumentSummary]:
    return [
        DocumentSummary(
            document_id=document.document_id,
            title=document.title,
            model_ids=list(document.model_ids),
            language=document.language,
            filename=document.filename,
            document_type=document.document_type,
        )
        for document in catalog.documents
    ]


def summarize_models(catalog: RegistryCatalog) -> list[CameraModel]:
    return [
        CameraModel(
            model_id=model.model_id,
            display_name=model.display_name,
            product_line=model.product_line,
        )
        for model in catalog.models
    ]


def _load_documents(path: Path) -> tuple[ManualDocumentRegistryEntry, ...]:
    raw_json = _read_text(path)
    try:
        return DOCUMENTS_ADAPTER.validate_json(raw_json)
    except ValidationError as error:
        raise RegistryValidationError([str(error)]) from error


def _load_models(path: Path) -> tuple[CameraModelRegistryEntry, ...]:
    raw_json = _read_text(path)
    try:
        return MODELS_ADAPTER.validate_json(raw_json)
    except ValidationError as error:
        raise RegistryValidationError([str(error)]) from error


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise RegistryValidationError(
            [f"missing registry file: {path.name}"],
        ) from error


def _validate_catalog(
    *,
    documents: tuple[ManualDocumentRegistryEntry, ...],
    models: tuple[CameraModelRegistryEntry, ...],
) -> None:
    errors: list[str] = []
    model_ids = tuple(model.model_id for model in models)
    document_ids = tuple(document.document_id for document in documents)
    errors.extend(_duplicate_errors(label="model_id", values=model_ids))
    errors.extend(_duplicate_errors(label="document_id", values=document_ids))

    known_models = set(model_ids)
    errors.extend(
        f"unknown model_id: {model_id} in {document.document_id}"
        for document in documents
        for model_id in document.model_ids
        if model_id not in known_models
    )

    if errors:
        raise RegistryValidationError(errors)


def _duplicate_errors(*, label: str, values: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen:
            duplicates.append(f"duplicate {label}: {value}")
        seen.add(value)
    return duplicates
