from fastapi import APIRouter

from backend.app.schemas.feature_card import FeatureCard

router = APIRouter()


@router.get("/{feature_id}", response_model=FeatureCard | None)
async def get_feature(feature_id: str) -> FeatureCard | None:
    return None
