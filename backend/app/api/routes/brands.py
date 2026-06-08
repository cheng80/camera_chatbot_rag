from fastapi import APIRouter

from backend.app.core.settings import get_settings
from backend.app.schemas.brand import BrandSummary
from backend.app.services.brand_registry import load_brand_catalog, summarize_brands

router = APIRouter()


@router.get("")
async def list_brands() -> list[BrandSummary]:
    settings = get_settings()
    catalog = load_brand_catalog(settings)
    return summarize_brands(catalog)
