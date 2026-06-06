from backend.app.main import create_app
from backend.app.schemas.document import CameraModel, DocumentSummary
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

DOCUMENTS_ADAPTER = TypeAdapter(list[DocumentSummary])
MODELS_ADAPTER = TypeAdapter(list[CameraModel])
REGISTERED_DOCUMENT_COUNT = 29
REGISTERED_MODEL_COUNT = 30


def test_documents_route_returns_registered_manuals() -> None:
    client = TestClient(create_app())

    response = client.get("/api/documents")
    documents = DOCUMENTS_ADAPTER.validate_python(response.json())

    assert response.status_code == 200
    assert len(documents) == REGISTERED_DOCUMENT_COUNT


def test_models_route_returns_registered_camera_models() -> None:
    client = TestClient(create_app())

    response = client.get("/api/models")
    models = MODELS_ADAPTER.validate_python(response.json())

    assert response.status_code == 200
    assert len(models) == REGISTERED_MODEL_COUNT
