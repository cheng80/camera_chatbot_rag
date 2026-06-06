from fastapi import APIRouter

from backend.app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
