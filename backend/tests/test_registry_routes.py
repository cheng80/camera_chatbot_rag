from backend.app.main import create_app
from backend.app.schemas.document import CameraModel, DocumentSummary
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

DOCUMENTS_ADAPTER = TypeAdapter(list[DocumentSummary])
MODELS_ADAPTER = TypeAdapter(list[CameraModel])
REGISTERED_DOCUMENT_COUNT = 32
REGISTERED_MODEL_COUNT = 34
RICOH_DOCUMENT_COUNT = 24
RICOH_MODEL_COUNT = 21


def test_brands_route_returns_registered_brands() -> None:
    client = TestClient(create_app())

    response = client.get("/api/brands")

    assert response.status_code == 200
    assert response.json() == [
        {
            "brand_id": "panasonic_lumix",
            "brand_name": "Panasonic LUMIX",
            "brand_mark": "PL",
        },
        {
            "brand_id": "ricoh",
            "brand_name": "Ricoh / PENTAX",
            "brand_mark": "R",
        },
    ]


def test_documents_route_returns_registered_manuals() -> None:
    client = TestClient(create_app())

    response = client.get("/api/documents")
    documents = DOCUMENTS_ADAPTER.validate_python(response.json())

    assert response.status_code == 200
    assert len(documents) == REGISTERED_DOCUMENT_COUNT


def test_documents_route_rejects_unknown_brand() -> None:
    client = TestClient(create_app())

    response = client.get("/api/documents?brand_id=sony")

    assert response.status_code == 404


def test_documents_route_returns_ricoh_manuals() -> None:
    client = TestClient(create_app())

    response = client.get("/api/documents?brand_id=ricoh")
    documents = DOCUMENTS_ADAPTER.validate_python(response.json())

    assert response.status_code == 200
    assert len(documents) == RICOH_DOCUMENT_COUNT


def test_models_route_returns_registered_camera_models() -> None:
    client = TestClient(create_app())

    response = client.get("/api/models")
    models = MODELS_ADAPTER.validate_python(response.json())

    assert response.status_code == 200
    assert len(models) == REGISTERED_MODEL_COUNT


def test_models_route_rejects_unknown_brand() -> None:
    client = TestClient(create_app())

    response = client.get("/api/models?brand_id=sony")

    assert response.status_code == 404


def test_models_route_returns_ricoh_camera_models() -> None:
    client = TestClient(create_app())

    response = client.get("/api/models?brand_id=ricoh")
    models = MODELS_ADAPTER.validate_python(response.json())

    assert response.status_code == 200
    assert len(models) == RICOH_MODEL_COUNT

