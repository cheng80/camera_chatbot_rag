from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class AppConfigResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    app_name: str
    brand_name: str
    brand_mark: str
