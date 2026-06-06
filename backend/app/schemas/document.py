from pydantic import BaseModel, ConfigDict


class CameraModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str
    display_name: str


class DocumentSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    model_ids: list[str]
    language: str = "ko"


class PageReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    page: int
