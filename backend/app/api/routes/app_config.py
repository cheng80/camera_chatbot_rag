from fastapi import APIRouter

from backend.app.core.settings import get_settings
from backend.app.schemas.app_config import AppConfigResponse
from backend.app.services.brand_registry import (
    load_brand_catalog,
    resolve_brand,
    summarize_brands,
)

router = APIRouter()


@router.get("/app-config")
async def app_config() -> AppConfigResponse:
    settings = get_settings()
    brand_catalog = load_brand_catalog(settings)
    active_brand = resolve_brand(
        settings=settings,
        brand_id=brand_catalog.active_brand_id,
    )
    return AppConfigResponse(
        app_name=settings.app_name,
        active_brand_id=brand_catalog.active_brand_id,
        brand_name=active_brand.brand_name,
        brand_mark=active_brand.brand_mark,
        brands=summarize_brands(brand_catalog),
    )
