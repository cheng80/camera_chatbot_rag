from fastapi import APIRouter

from backend.app.core.settings import get_settings
from backend.app.schemas.app_config import AppConfigResponse

router = APIRouter()


@router.get("/app-config")
async def app_config() -> AppConfigResponse:
    settings = get_settings()
    return AppConfigResponse(
        app_name=settings.app_name,
        brand_name=settings.brand_name,
        brand_mark=settings.brand_mark,
    )
