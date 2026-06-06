from fastapi import APIRouter

from backend.app.core.settings import get_settings
from backend.app.schemas.document import DocumentSummary
from backend.app.services.registry import load_registry, summarize_documents

router = APIRouter()


@router.get("")
async def list_documents() -> list[DocumentSummary]:
    settings = get_settings()
    catalog = load_registry(settings.data_dir / "registry")
    return summarize_documents(catalog)
