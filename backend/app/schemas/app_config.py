from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.brand import BrandSummary


class AppConfigResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    app_name: str
    active_brand_id: str
    brand_name: str
    brand_mark: str
    brands: list[BrandSummary]
