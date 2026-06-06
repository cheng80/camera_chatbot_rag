from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    status: Literal["ok"]
