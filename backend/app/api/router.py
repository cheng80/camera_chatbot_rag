from fastapi import APIRouter

from backend.app.api.routes import (
    documents,
    features,
    feedback,
    health,
    models,
    search,
    viewer,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(features.router, prefix="/features", tags=["features"])
api_router.include_router(viewer.router, prefix="/viewer", tags=["viewer"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
