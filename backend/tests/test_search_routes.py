from backend.app.main import create_app
from fastapi.testclient import TestClient


def test_search_route_rejects_blank_query() -> None:
    client = TestClient(create_app())

    response = client.post("/api/search", json={"query": "   \t\n"})

    assert response.status_code == 422


def test_search_route_rejects_oversized_query() -> None:
    client = TestClient(create_app())

    response = client.post("/api/search", json={"query": "제" * 301})

    assert response.status_code == 422


def test_search_route_rejects_unsafe_model_id() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={"query": "제브라", "model_ids": ["../../bad"]},
    )

    assert response.status_code == 422
