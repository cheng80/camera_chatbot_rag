import re
from pathlib import Path
from typing import Annotated, Final

from fastapi import APIRouter, HTTPException
from fastapi import Path as ApiPath
from pydantic import TypeAdapter

from backend.app.core.settings import get_settings
from backend.app.indexing.pdf_extractor import ExtractedPage
from backend.app.schemas.document import PageReference
from backend.app.services.registry import load_registry

router = APIRouter()
SAFE_DOCUMENT_ID_RE: Final = re.compile(r"^[a-z0-9_]+$")
PAGES_ADAPTER: Final[TypeAdapter[tuple[ExtractedPage, ...]]] = TypeAdapter(
    tuple[ExtractedPage, ...],
)


@router.get("/{document_id}/pages/{page}")
async def get_page_reference(
    document_id: str,
    page: Annotated[int, ApiPath(ge=1)],
) -> PageReference:
    if SAFE_DOCUMENT_ID_RE.fullmatch(document_id) is None:
        raise HTTPException(status_code=400, detail="unsafe document_id")

    settings = get_settings()
    catalog = load_registry(settings.data_dir / "registry")
    known_document_ids = {document.document_id for document in catalog.documents}
    if document_id not in known_document_ids:
        raise HTTPException(status_code=404, detail="document not found")

    pages_path = settings.data_dir / "processed" / "pages" / f"{document_id}.jsonl"
    if not pages_path.is_file():
        raise HTTPException(status_code=404, detail="processed pages not found")

    pages = _load_document_pages(pages_path)
    known_pages = {processed_page.page for processed_page in pages}
    if page not in known_pages:
        raise HTTPException(status_code=404, detail="page not found")

    return PageReference(
        document_id=document_id,
        page=page,
        image_url=f"/page-images/{document_id}/{page}.png",
    )


def _load_document_pages(path: Path) -> tuple[ExtractedPage, ...]:
    content = f"[{','.join(path.read_text(encoding='utf-8').splitlines())}]"
    return PAGES_ADAPTER.validate_json(content)
