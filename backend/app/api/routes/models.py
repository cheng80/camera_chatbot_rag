from fastapi import APIRouter

from backend.app.core.settings import get_settings
from backend.app.schemas.document import CameraModel
from backend.app.services.registry import load_registry, summarize_models

router = APIRouter()


@router.get("")
async def list_models() -> list[CameraModel]:
    settings = get_settings()
    catalog = load_registry(settings.data_dir / "registry")
    return summarize_models(catalog)
