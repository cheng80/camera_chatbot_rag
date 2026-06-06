import json
import re
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

from backend.app.schemas.document import (
    CameraModelRegistryEntry,
    ManualDocumentRegistryEntry,
    RegistryCatalog,
)
from backend.app.services.registry import (
    load_registry,
)

MODEL_ID_RE: Final = re.compile(r"\b(?:DC|DMC)-[A-Z0-9]+[A-Z]?\b")
BARE_MODEL_RE: Final = re.compile(r"\b[A-Z]{1,3}[0-9][A-Z0-9]*\b")
type AutoRegistrationStatus = Literal[
    "auto_registerable",
    "already_registered",
    "blocked",
]


class AutoPdfRegistrationPlan(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    status: AutoRegistrationStatus
    pdf_path: Path
    confidence: float = Field(ge=0, le=1)
    document: ManualDocumentRegistryEntry | None = None
    model: CameraModelRegistryEntry | None = None
    reasons: tuple[str, ...]
    block_reasons: tuple[str, ...] = ()


def plan_pdf_auto_registration(
    *,
    pdf_path: Path,
    catalog: RegistryCatalog,
    manuals_dir: Path,
    first_pages_text: str | None = None,
) -> AutoPdfRegistrationPlan:
    if not pdf_path.is_file():
        return _blocked(pdf_path=pdf_path, reason="pdf_missing")
    if pdf_path.parent.resolve() != manuals_dir.resolve():
        return _blocked(pdf_path=pdf_path, reason="pdf_not_under_manuals_dir")
    existing = _existing_document_for_pdf(pdf_path=pdf_path, catalog=catalog)
    if existing is not None:
        return AutoPdfRegistrationPlan(
            status="already_registered",
            pdf_path=pdf_path,
            confidence=1,
            document=existing,
            model=_existing_model(model_id=existing.model_ids[0], catalog=catalog),
            reasons=("filename_already_registered",),
        )
    text = first_pages_text
    if text is None:
        text = read_first_pages_text(pdf_path=pdf_path, page_limit=3)
    return _plan_from_text(pdf_path=pdf_path, catalog=catalog, text=text)


def append_auto_registration(
    *,
    plan: AutoPdfRegistrationPlan,
    registry_dir: Path,
) -> None:
    if plan.status != "auto_registerable" or plan.document is None:
        return
    catalog = load_registry(registry_dir)
    documents = (*catalog.documents, plan.document)
    models = catalog.models
    if plan.model is not None and plan.model.model_id not in {
        model.model_id for model in catalog.models
    }:
        models = (*models, plan.model)
    _write_documents_json(path=registry_dir / "documents.json", items=documents)
    _write_models_json(path=registry_dir / "models.json", items=models)


def read_first_pages_text(*, pdf_path: Path, page_limit: int) -> str:
    reader = PdfReader(pdf_path)
    texts = tuple(
        reader.pages[index].extract_text() or ""
        for index in range(min(page_limit, len(reader.pages)))
    )
    return "\n".join(texts)


def _plan_from_text(
    *,
    pdf_path: Path,
    catalog: RegistryCatalog,
    text: str,
) -> AutoPdfRegistrationPlan:
    filename_models = _model_ids_from_filename(pdf_path.stem)
    if not filename_models:
        return _blocked(pdf_path=pdf_path, reason="filename_model_missing")
    text_models = set(MODEL_ID_RE.findall(text))
    missing_text_models = tuple(
        model_id for model_id in filename_models if model_id not in text_models
    )
    if missing_text_models:
        return _blocked(pdf_path=pdf_path, reason="model_not_confirmed_by_pdf_text")
    document_type = _document_type(text)
    if document_type is None:
        return _blocked(pdf_path=pdf_path, reason="document_type_unknown")
    document_id = _document_id(model_ids=filename_models, document_type=document_type)
    if document_id in {document.document_id for document in catalog.documents}:
        return _blocked(pdf_path=pdf_path, reason="document_id_duplicate")
    model_id = filename_models[0]
    document = ManualDocumentRegistryEntry(
        document_id=document_id,
        title=_title(model_id=model_id, document_type=document_type),
        filename=pdf_path.name,
        model_ids=filename_models,
        language="ko",
        document_type=document_type,
    )
    model = _existing_model(model_id=model_id, catalog=catalog) or _model(model_id)
    return AutoPdfRegistrationPlan(
        status="auto_registerable",
        pdf_path=pdf_path,
        confidence=1,
        document=document,
        model=model,
        reasons=("filename_model_confirmed", "document_type_confirmed"),
    )


def _model_ids_from_filename(stem: str) -> tuple[str, ...]:
    direct = tuple(MODEL_ID_RE.findall(stem.upper()))
    if direct:
        return direct
    return ()


def _document_type(
    text: str,
) -> Literal["full_manual", "advanced_manual", "operating_instructions"] | None:
    if "전체 안내서" in text:
        return "full_manual"
    if "고급 기능 사용 설명서" in text:
        return "advanced_manual"
    if "기본 사용 설명서" in text:
        return "operating_instructions"
    return None


def _document_id(
    *,
    model_ids: tuple[str, ...],
    document_type: str,
) -> str:
    base = "_".join(model_id.lower().replace("-", "_") for model_id in model_ids)
    if document_type == "full_manual":
        return f"{base}_full_kor"
    return f"{base}_kor"


def _title(*, model_id: str, document_type: str) -> str:
    title_type = {
        "full_manual": "전체 안내서",
        "advanced_manual": "고급 기능 사용 설명서",
        "operating_instructions": "기본 사용 설명서",
    }[document_type]
    return f"{model_id} {title_type}"


def _model(model_id: str) -> CameraModelRegistryEntry:
    return CameraModelRegistryEntry(
        model_id=model_id,
        display_name=f"LUMIX {model_id.split('-', maxsplit=1)[1]}",
        product_line=_product_line(model_id),
    )


def _product_line(model_id: str) -> str:
    suffix = model_id.split("-", maxsplit=1)[1]
    line = BARE_MODEL_RE.match(suffix)
    if line is None:
        return "LUMIX"
    if suffix.startswith("S"):
        return "LUMIX S"
    if suffix.startswith("TZ"):
        return "LUMIX TZ"
    if suffix.startswith("ZS"):
        return "LUMIX ZS"
    if suffix.startswith("LX"):
        return "LUMIX LX"
    return "LUMIX G"


def _existing_document_for_pdf(
    *,
    pdf_path: Path,
    catalog: RegistryCatalog,
) -> ManualDocumentRegistryEntry | None:
    for document in catalog.documents:
        if document.filename == pdf_path.name:
            return document
    return None


def _existing_model(
    *,
    model_id: str,
    catalog: RegistryCatalog,
) -> CameraModelRegistryEntry | None:
    for model in catalog.models:
        if model.model_id == model_id:
            return model
    return None


def _blocked(*, pdf_path: Path, reason: str) -> AutoPdfRegistrationPlan:
    return AutoPdfRegistrationPlan(
        status="blocked",
        pdf_path=pdf_path,
        confidence=0,
        reasons=(),
        block_reasons=(reason,),
    )


def _write_documents_json(
    *,
    path: Path,
    items: tuple[ManualDocumentRegistryEntry, ...],
) -> None:
    _ = path.write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in items],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_models_json(
    *,
    path: Path,
    items: tuple[CameraModelRegistryEntry, ...],
) -> None:
    _ = path.write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in items],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
