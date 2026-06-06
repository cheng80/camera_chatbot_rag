from fastapi import APIRouter

from backend.app.schemas.feature_card import FeatureCard

router = APIRouter()


@router.get("/{feature_id}")
async def get_feature(feature_id: str) -> FeatureCard | None:
    del feature_id
    return None
