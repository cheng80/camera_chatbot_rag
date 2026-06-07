from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

import httpx2
from backend.app.core.settings import Settings
from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
    SupportedModel,
)
from backend.app.schemas.search import NormalizedQuery, SearchResponse
from backend.app.services.answer_rewrite import (
    rewrite_search_response,
    rewrite_selected_card_summary,
    warm_up_answer_rewrite,
)

type SettingsFactory = Callable[..., Settings]


@dataclass(slots=True)
class FakeRewriteClient:
    responses: list[str | Exception]
    tried_models: list[str] = field(default_factory=list)

    def rewrite(
        self,
        *,
        model_id: str,
        query: str,
        card: FeatureCard,
        max_tokens: int,
        think: bool,
    ) -> str:
        _ = (query, card, max_tokens, think)
        self.tried_models.append(model_id)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_rewrite_search_response_updates_first_card_summary() -> None:
    settings = _settings()
    client = FakeRewriteClient(
        responses=["밝은 부분에 줄무늬를 표시합니다."],
    )
    response = _search_response(cards=(_card(feature_name="제브라 패턴"),))

    rewritten = rewrite_search_response(
        response=response,
        settings=settings,
        client=client,
    )

    assert rewritten.cards[0].summary == "제브라 패턴: 밝은 부분에 줄무늬를 표시합니다."
    assert rewritten.cards[0].sources == response.cards[0].sources
    assert client.tried_models == [settings.llm_rewrite_model]


def test_rewrite_search_response_uses_fallback_model() -> None:
    settings = _settings()
    client = FakeRewriteClient(
        responses=[
            httpx2.ConnectError("down"),
            "DC-G9M2 매뉴얼 415쪽에서 확인하세요.",
        ],
    )
    response = _search_response(cards=(_card(feature_name="제브라 패턴"),))

    rewritten = rewrite_search_response(
        response=response,
        settings=settings,
        client=client,
    )

    assert rewritten.cards[0].summary.startswith("제브라 패턴:")
    assert client.tried_models == [
        settings.llm_rewrite_model,
        settings.llm_rewrite_fallback_models[0],
    ]


def test_rewrite_search_response_respects_disabled_setting() -> None:
    settings = _settings(llm_rewrite_enabled=False)
    client = FakeRewriteClient(responses=["unused"])
    response = _search_response(cards=(_card(feature_name="제브라 패턴"),))

    rewritten = rewrite_search_response(
        response=response,
        settings=settings,
        client=client,
    )

    assert rewritten == response
    assert client.tried_models == []


def test_rewrite_search_response_keeps_extra_cards_unchanged() -> None:
    settings = _settings()
    client = FakeRewriteClient(responses=["첫 번째 답변입니다."])
    response = _search_response(
        cards=(
            _card(feature_name="제브라 패턴"),
            _card(feature_name="손떨림 보정"),
        ),
    )

    rewritten = rewrite_search_response(
        response=response,
        settings=settings,
        client=client,
    )

    assert rewritten.cards[0].summary == "제브라 패턴: 첫 번째 답변입니다."
    assert rewritten.cards[1].summary == response.cards[1].summary


def test_rewrite_search_response_cleans_rewritten_pdf_menu_noise() -> None:
    settings = _settings()
    client = FakeRewriteClient(
        responses=[
            "> > [프록시 기록 설정] > [실시간 LUT(프록시)] 선택: 하이브리드 줌 동영상",
        ],
    )
    response = _search_response(cards=(_card(feature_name="하이브리드 줌"),))

    rewritten = rewrite_search_response(
        response=response,
        settings=settings,
        client=client,
    )

    assert rewritten.cards[0].summary == "하이브리드 줌 동영상"


def test_rewrite_search_response_keeps_parenthesized_subject_suffix() -> None:
    settings = _settings()
    client = FakeRewriteClient(
        responses=["동영상 촬영에서 하이브리드 줌을 설정합니다."],
    )
    response = _search_response(cards=(_card(feature_name="하이브리드 줌(동영상)"),))

    rewritten = rewrite_search_response(
        response=response,
        settings=settings,
        client=client,
    )

    assert rewritten.cards[0].summary.startswith("하이브리드 줌(동영상):")


def test_warm_up_answer_rewrite_uses_primary_model_when_enabled() -> None:
    settings = _settings(llm_rewrite_warmup_enabled=True)
    client = FakeRewriteClient(responses=["제브라 패턴: 줄무늬를 표시합니다."])

    warmed = warm_up_answer_rewrite(settings=settings, client=client)

    assert warmed is True
    assert client.tried_models == [settings.llm_rewrite_model]


def test_rewrite_selected_card_summary_updates_one_card() -> None:
    settings = _settings()
    client = FakeRewriteClient(responses=["밝은 부분에 줄무늬를 표시합니다."])

    summary = rewrite_selected_card_summary(
        query="제브라 패턴은 뭐야?",
        card=_card(feature_name="제브라 패턴"),
        settings=settings,
        client=client,
    )

    assert summary == "제브라 패턴: 밝은 부분에 줄무늬를 표시합니다."
    assert client.tried_models == [settings.llm_rewrite_model]


def test_rewrite_selected_card_summary_respects_disabled_setting() -> None:
    settings = _settings(llm_rewrite_enabled=False)
    client = FakeRewriteClient(responses=["unused"])

    summary = rewrite_selected_card_summary(
        query="제브라 패턴은 뭐야?",
        card=_card(feature_name="제브라 패턴"),
        settings=settings,
        client=client,
    )

    assert summary is None
    assert client.tried_models == []


def test_warm_up_answer_rewrite_respects_disabled_setting() -> None:
    settings = _settings(llm_rewrite_warmup_enabled=False)
    client = FakeRewriteClient(responses=["unused"])

    warmed = warm_up_answer_rewrite(settings=settings, client=client)

    assert warmed is False
    assert client.tried_models == []


def _search_response(*, cards: tuple[FeatureCard, ...]) -> SearchResponse:
    return SearchResponse(
        query="제브라 패턴",
        normalized_query=NormalizedQuery(
            intent="feature_search",
            terms=["제브라 패턴"],
            search_query="제브라 패턴",
        ),
        cards=list(cards),
        retrieval_status="ok",
    )


def _settings(**overrides: object) -> Settings:
    settings_factory = cast("SettingsFactory", Settings)
    return settings_factory(_env_file=None, **overrides)


def _card(*, feature_name: str) -> FeatureCard:
    return FeatureCard(
        feature_id=feature_name,
        feature_name=feature_name,
        category="manual_chunk",
        summary="DC-G9M2 매뉴얼 415쪽에서 확인하세요.",
        supported_models=[
            SupportedModel(model_id="DC-G9M2", support_status="unknown"),
        ],
        sources=[
            SourceReference(
                document_id="dc_g9m2_full_kor",
                model_id="DC-G9M2",
                page=415,
                section_title=feature_name,
                viewer_url="/api/viewer/dc_g9m2_full_kor/pages/415",
            ),
        ],
        confidence=0.55,
    )
