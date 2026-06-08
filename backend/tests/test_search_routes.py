from backend.app.main import create_app
from backend.app.schemas.search import SearchResponse
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


def test_search_route_accepts_large_display_count() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={"query": "하이브리드 줌", "top_k": 1000},
    )

    assert response.status_code == 200


def test_search_route_adds_selected_brand_to_viewer_urls() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={
            "query": "제브라 패턴",
            "brand_id": "panasonic_lumix",
            "top_k": 1,
        },
    )

    assert response.status_code == 200
    search_response = SearchResponse.model_validate(response.json())
    assert search_response.cards
    assert search_response.cards[0].sources[0].viewer_url.endswith(
        "?brand_id=panasonic_lumix",
    )


def test_search_route_rejects_unknown_brand() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={"query": "제브라 패턴", "brand_id": "sony"},
    )

    assert response.status_code == 404


def test_search_expand_route_rejects_unsafe_brand() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search/expand",
        json={"query": "배터리 충전", "brand_id": "../bad"},
    )

    assert response.status_code == 422


def test_search_route_uses_ricoh_brand_model_aliases() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={
            "query": "GR III 초점",
            "brand_id": "ricoh",
            "top_k": 1,
        },
    )

    assert response.status_code == 200
    search_response = SearchResponse.model_validate(response.json())
    assert search_response.normalized_query.detected_model_ids == ["RICOH-GR-III"]
    assert search_response.normalized_query.search_query == "초점"
