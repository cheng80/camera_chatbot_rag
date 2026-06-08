from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

import httpx2
from backend.app.core.settings import Settings
from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
)
from backend.app.schemas.search import NormalizedQuery, SearchRequest, SearchResponse
from backend.app.services.search_context_expander import expand_search_response

type SettingsFactory = Callable[..., Settings]


@dataclass(slots=True)
class FakeExpansionClient:
    responses: list[str | Exception]
    tried_models: list[str] = field(default_factory=list)

    def expand(
        self,
        *,
        model_id: str,
        query: str,
        max_terms: int,
        max_tokens: int,
        think: bool,
    ) -> str:
        _ = (query, max_terms, max_tokens, think)
        self.tried_models.append(model_id)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_expand_search_response_merges_llm_expanded_queries() -> None:
    settings = _settings()
    client = FakeExpansionClient(responses=["배터리 충전\n충전 램프\nUSB 전원"])
    searched_queries: list[str] = []

    response = expand_search_response(
        payload=SearchRequest(query="내장 베터리 충전 안됨", top_k=5),
        settings=settings,
        search_runner=_search_runner(searched_queries),
        client=client,
    )

    assert response.status == "ok"
    assert response.expanded_queries == ["배터리 충전", "충전 램프", "USB 전원"]
    assert searched_queries == [
        "내장 베터리 충전 안됨",
        "배터리 충전",
        "충전 램프",
        "USB 전원",
    ]
    assert [card.feature_name for card in response.response.cards] == [
        "배터리 충전",
        "충전 램프",
        "USB 전원",
        "내장 베터리 충전 안됨",
    ]


def test_expand_search_response_uses_fallback_model() -> None:
    settings = _settings()
    client = FakeExpansionClient(
        responses=[
            httpx2.ConnectError("down"),
            "초점 피킹\nMF 보조",
        ],
    )

    response = expand_search_response(
        payload=SearchRequest(query="수동 초점 잘 보이게", top_k=5),
        settings=settings,
        search_runner=_search_runner([]),
        client=client,
    )

    assert response.status == "ok"
    assert response.expanded_queries == ["초점 피킹", "MF 보조"]
    assert client.tried_models == [
        settings.llm_query_expansion_model,
        settings.llm_query_expansion_fallback_models[0],
    ]


def test_expand_search_response_respects_disabled_setting() -> None:
    settings = _settings(llm_query_expansion_enabled=False)
    client = FakeExpansionClient(responses=["unused"])

    response = expand_search_response(
        payload=SearchRequest(query="배터리 충전", top_k=5),
        settings=settings,
        search_runner=_search_runner([]),
        client=client,
    )

    assert response.status == "unavailable"
    assert response.expanded_queries == []
    assert response.response.cards[0].feature_name == "배터리 충전"
    assert client.tried_models == []


def test_expand_search_response_deduplicates_same_source_page() -> None:
    settings = _settings()
    client = FakeExpansionClient(responses=["배터리 충전\n충전 방법"])

    response = expand_search_response(
        payload=SearchRequest(query="배터리", top_k=5),
        settings=settings,
        search_runner=_duplicate_source_runner,
        client=client,
    )

    assert len(response.response.cards) == 1
    assert response.response.cards[0].feature_name == "배터리"


def test_expand_search_response_caps_added_cards() -> None:
    settings = _settings()
    client = FakeExpansionClient(responses=["배터리 확장"])

    response = expand_search_response(
        payload=SearchRequest(query="배터리", top_k=1000),
        settings=settings,
        search_runner=_many_expanded_cards_runner,
        client=client,
    )

    assert len(response.response.cards) == 25
    assert response.response.cards[0].feature_name == "배터리 확장 1"
    assert response.response.cards[23].feature_name == "배터리 확장 24"
    assert response.response.cards[24].feature_name == "배터리"


def test_expand_search_response_filters_irrelevant_added_cards() -> None:
    settings = _settings()
    client = FakeExpansionClient(responses=["날짜 설정 변경"])

    response = expand_search_response(
        payload=SearchRequest(query="배터리 날짜 초기화", top_k=10),
        settings=settings,
        search_runner=_mixed_relevance_runner,
        client=client,
    )

    assert [card.feature_name for card in response.response.cards] == [
        "날짜 설정",
        "배터리 날짜 초기화",
    ]


def _search_runner(
    searched_queries: list[str],
) -> Callable[[SearchRequest], SearchResponse]:
    def run(payload: SearchRequest) -> SearchResponse:
        searched_queries.append(payload.query)
        return _search_response(query=payload.query, page=len(searched_queries))

    return run


def _duplicate_source_runner(payload: SearchRequest) -> SearchResponse:
    return _search_response(query=payload.query, page=1)


def _many_expanded_cards_runner(payload: SearchRequest) -> SearchResponse:
    if payload.query == "배터리":
        return _search_response(query=payload.query, page=1000)
    return SearchResponse(
        query=payload.query,
        normalized_query=NormalizedQuery(
            intent="feature_search",
            terms=[payload.query],
            search_query=payload.query,
        ),
        cards=[
            _card(
                feature_name=f"{payload.query} {index}",
                page=index,
            )
            for index in range(1, payload.top_k + 1)
        ],
        retrieval_status="ok",
    )


def _mixed_relevance_runner(payload: SearchRequest) -> SearchResponse:
    if payload.query == "배터리 날짜 초기화":
        return _search_response(query=payload.query, page=1)
    return SearchResponse(
        query=payload.query,
        normalized_query=NormalizedQuery(
            intent="feature_search",
            terms=[payload.query],
            search_query=payload.query,
        ),
        cards=[
            _card(feature_name="날짜 설정", page=2),
            _card(feature_name="저작권 정보 저작권 정보 첨부", page=3),
        ],
        retrieval_status="ok",
    )


def _search_response(*, query: str, page: int) -> SearchResponse:
    return SearchResponse(
        query=query,
        normalized_query=NormalizedQuery(
            intent="feature_search",
            terms=[query],
            search_query=query,
        ),
        cards=[
            _card(feature_name=query, page=page),
        ],
        retrieval_status="ok",
    )


def _card(*, feature_name: str, page: int) -> FeatureCard:
    return FeatureCard(
        feature_id=f"card:{page}",
        feature_name=feature_name,
        category="manual_chunk",
        summary=feature_name,
        supported_models=[],
        sources=[
            SourceReference(
                document_id="manual",
                model_id="MODEL",
                page=page,
                section_title=feature_name,
                viewer_url=f"/api/viewer/manual/pages/{page}",
            ),
        ],
        confidence=0.55,
    )


def _settings(**overrides: object) -> Settings:
    settings_factory = cast("SettingsFactory", Settings)
    return settings_factory(_env_file=None, **overrides)
