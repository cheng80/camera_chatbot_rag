from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.settings import get_settings
from backend.app.schemas.document import DocumentSummary
from backend.app.services.brand_data_paths import brand_data_paths
from backend.app.services.brand_registry import BrandRegistryError, resolve_brand
from backend.app.services.registry import load_registry, summarize_documents

router = APIRouter()


@router.get("")
async def list_documents(
    brand_id: Annotated[str | None, Query(max_length=64)] = None,
) -> list[DocumentSummary]:
    settings = get_settings()
    try:
        brand = resolve_brand(settings=settings, brand_id=brand_id)
    except BrandRegistryError as error:
        raise HTTPException(status_code=404, detail=error.errors) from error
    catalog = load_registry(brand_data_paths(brand.data_dir).registry_dir)
    return summarize_documents(catalog)
