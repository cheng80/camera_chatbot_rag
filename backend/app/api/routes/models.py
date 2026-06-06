from fastapi import APIRouter

from backend.app.schemas.document import CameraModel

router = APIRouter()


@router.get("")
async def list_models() -> list[CameraModel]:
    return []
