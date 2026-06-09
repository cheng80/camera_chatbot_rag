import pytest
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


def test_search_route_can_include_feature_wiki_candidates() -> None:
    client = TestClient(create_app())

    baseline_response = client.post(
        "/api/search",
        json={
            "query": "제브라 패턴",
            "brand_id": "panasonic_lumix",
            "top_k": 2,
        },
    )
    opt_in_response = client.post(
        "/api/search",
        json={
            "query": "제브라 패턴",
            "brand_id": "panasonic_lumix",
            "top_k": 2,
            "include_feature_wiki_candidates": True,
        },
    )

    assert baseline_response.status_code == 200
    assert opt_in_response.status_code == 200
    baseline = SearchResponse.model_validate(baseline_response.json())
    opt_in = SearchResponse.model_validate(opt_in_response.json())
    baseline_ids = [card.feature_id for card in baseline.cards]
    wiki_cards = [
        card for card in opt_in.cards if card.feature_id.startswith("feature_wiki:")
    ]
    assert not [
        feature_id
        for feature_id in baseline_ids
        if feature_id.startswith("feature_wiki:")
    ]
    assert baseline_ids == [
        card.feature_id for card in opt_in.cards[: len(baseline_ids)]
    ]
    assert wiki_cards
    zebra_card = next(
        card for card in wiki_cards if card.feature_id == "feature_wiki:제브라_패턴"
    )
    multi_label_card = next(
        card for card in wiki_cards if card.feature_id == "feature_wiki:zebra1_zebra2"
    )
    assert zebra_card.feature_name == "제브라 패턴"
    assert multi_label_card.feature_name == "[ZEBRA1] [ZEBRA2]"
    assert zebra_card.sources
    assert zebra_card.sources[0].viewer_url.endswith(
        "?brand_id=panasonic_lumix",
    )
    assert zebra_card.evidence_status == "source_validated"


def test_search_route_promotes_wiki_for_natural_language_query() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={
            "query": "과노출 경고 줄무늬 어디서 켜?",
            "brand_id": "panasonic_lumix",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    search_response = SearchResponse.model_validate(response.json())
    assert search_response.cards
    first_card = search_response.cards[0]
    assert first_card.feature_id == "feature_wiki:제브라_패턴"
    assert first_card.feature_name == "제브라 패턴"
    assert first_card.evidence_status == "source_validated"


@pytest.mark.parametrize("query", ["초점", "설정", "기능", "어디"])
def test_search_route_keeps_broad_single_token_queries_on_baseline(
    query: str,
) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={
            "query": query,
            "brand_id": "panasonic_lumix",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    search_response = SearchResponse.model_validate(response.json())
    if search_response.cards:
        assert not search_response.cards[0].feature_id.startswith("feature_wiki:")


def test_search_route_opt_in_filters_instruction_like_wiki_labels() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={
            "query": "패턴",
            "brand_id": "panasonic_lumix",
            "top_k": 5,
            "include_feature_wiki_candidates": True,
        },
    )

    assert response.status_code == 200
    search_response = SearchResponse.model_validate(response.json())
    wiki_cards = tuple(
        card
        for card in search_response.cards
        if card.feature_id.startswith("feature_wiki:")
    )
    assert wiki_cards
    wiki_ids = [card.feature_id for card in wiki_cards]
    assert "feature_wiki:제브라_패턴" in wiki_ids
    noisy_ids = {
        "feature_wiki:3_3421를_눌러_af_영역의_위치를_옮기십시오",
    }
    assert not noisy_ids.intersection(wiki_ids)


def test_feature_wiki_opt_in_does_not_change_blank_query_validation() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/search",
        json={
            "query": "   \t\n",
            "brand_id": "panasonic_lumix",
            "include_feature_wiki_candidates": True,
        },
    )

    assert response.status_code == 422
