from dataclasses import dataclass, field
from types import TracebackType
from typing import ClassVar, Protocol, Self

import httpx2
from pydantic import BaseModel, ConfigDict

from backend.app.core.settings import Settings
from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
    SupportedModel,
)
from backend.app.schemas.search import SearchResponse
from backend.app.services.retrieval_display_text import clean_summary_text

DEFAULT_REWRITE_CARD_LIMIT = 1


class AnswerRewriteClient(Protocol):
    def rewrite(
        self,
        *,
        model_id: str,
        query: str,
        card: FeatureCard,
        max_tokens: int,
        think: bool,
    ) -> str: ...


class OllamaChatMessage(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    content: str = ""


class OllamaChatResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    message: OllamaChatMessage


@dataclass(slots=True)
class OllamaAnswerRewriteClient:
    settings: Settings
    _client: httpx2.Client = field(init=False)

    def __post_init__(self) -> None:
        self._client = httpx2.Client(timeout=self.settings.llm_request_timeout_seconds)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._client.close()

    def rewrite(
        self,
        *,
        model_id: str,
        query: str,
        card: FeatureCard,
        max_tokens: int,
        think: bool,
    ) -> str:
        response = self._client.post(
            _ollama_chat_url(self.settings.llm_base_url),
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
            json={
                "model": model_id,
                "messages": _rewrite_messages(query=query, card=card),
                "stream": False,
                "think": think,
                "options": {
                    "temperature": self.settings.llm_temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        _ = response.raise_for_status()
        parsed = OllamaChatResponse.model_validate_json(response.text)
        return parsed.message.content.strip()


def rewrite_search_response(
    *,
    response: SearchResponse,
    settings: Settings,
    client: AnswerRewriteClient | None = None,
    card_limit: int = DEFAULT_REWRITE_CARD_LIMIT,
) -> SearchResponse:
    if not settings.llm_rewrite_enabled or not response.cards or card_limit < 1:
        return response
    if client is None:
        with OllamaAnswerRewriteClient(settings=settings) as rewrite_client:
            return _rewrite_with_client(
                response=response,
                settings=settings,
                client=rewrite_client,
                card_limit=card_limit,
            )
    return _rewrite_with_client(
        response=response,
        settings=settings,
        client=client,
        card_limit=card_limit,
    )


def rewrite_selected_card_summary(
    *,
    query: str,
    card: FeatureCard,
    settings: Settings,
    client: AnswerRewriteClient | None = None,
) -> str | None:
    if not settings.llm_rewrite_enabled:
        return None
    if client is None:
        with OllamaAnswerRewriteClient(settings=settings) as rewrite_client:
            return _rewrite_selected_card_summary_with_client(
                query=query,
                card=card,
                settings=settings,
                client=rewrite_client,
            )
    return _rewrite_selected_card_summary_with_client(
        query=query,
        card=card,
        settings=settings,
        client=client,
    )


def warm_up_answer_rewrite(
    *,
    settings: Settings,
    client: AnswerRewriteClient | None = None,
) -> bool:
    if not settings.llm_rewrite_enabled or not settings.llm_rewrite_warmup_enabled:
        return False
    warmup_card = _warmup_card()
    if client is None:
        with OllamaAnswerRewriteClient(settings=settings) as rewrite_client:
            return _rewrite_card_summary(
                query="제브라 패턴",
                card=warmup_card,
                settings=settings,
                client=rewrite_client,
            ) is not None
    return (
        _rewrite_card_summary(
            query="제브라 패턴",
            card=warmup_card,
            settings=settings,
            client=client,
        )
        is not None
    )


def _rewrite_with_client(
    *,
    response: SearchResponse,
    settings: Settings,
    client: AnswerRewriteClient,
    card_limit: int,
) -> SearchResponse:
    cards = list(response.cards)
    for index, card in enumerate(cards[:card_limit]):
        rewritten = _rewrite_card_summary(
            query=response.query,
            card=card,
            settings=settings,
            client=client,
        )
        if rewritten:
            cards[index] = card.model_copy(
                update={
                    "summary": _subject_prefixed_summary(
                        subject=card.feature_name,
                        summary=rewritten,
                    ),
                },
            )
    return response.model_copy(update={"cards": cards})


def _rewrite_selected_card_summary_with_client(
    *,
    query: str,
    card: FeatureCard,
    settings: Settings,
    client: AnswerRewriteClient,
) -> str | None:
    rewritten = _rewrite_card_summary(
        query=query,
        card=card,
        settings=settings,
        client=client,
    )
    if not rewritten:
        return None
    return _subject_prefixed_summary(subject=card.feature_name, summary=rewritten)


def _rewrite_card_summary(
    *,
    query: str,
    card: FeatureCard,
    settings: Settings,
    client: AnswerRewriteClient,
) -> str | None:
    if card.evidence_status != "source_validated" or not card.sources:
        return None
    for model_id in _rewrite_model_ids(settings):
        try:
            rewritten = client.rewrite(
                model_id=model_id,
                query=query,
                card=card,
                max_tokens=settings.llm_rewrite_max_tokens,
                think=settings.llm_rewrite_think,
            )
        except httpx2.HTTPError:
            continue
        if rewritten:
            return rewritten
    return None


def _rewrite_model_ids(settings: Settings) -> tuple[str, ...]:
    return (settings.llm_rewrite_model, *settings.llm_rewrite_fallback_models)


def _rewrite_messages(
    *,
    query: str,
    card: FeatureCard,
) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": (
                "Rewrite the verified camera-manual answer as plain Korean text only. "
                "Do not output JSON, markdown, source refs, analysis, or reasoning. "
                "Use at most two short sentences. Do not add facts. "
                "Do not add verbs, feature names, menu names, or options that are not "
                "present in the verified answer."
            ),
        },
        {
            "role": "user",
            "content": (
                f"User query:\n{query}\n\n"
                f"Feature name:\n{card.feature_name}\n\n"
                f"Verified answer:\n{card.summary}\n\n"
                f"Verified source pages:\n{_source_page_text(card)}\n\n"
                "Return only the rewritten Korean answer text. Use only words and "
                "claims grounded in the verified answer."
            ),
        },
    )


def _source_page_text(card: FeatureCard) -> str:
    return ", ".join(
        f"{source.document_id}/{source.model_id}/{source.page}"
        for source in card.sources
    )


def _subject_prefixed_summary(*, subject: str, summary: str) -> str:
    answer = clean_summary_text(" ".join(summary.split()).strip())
    clean_subject = " ".join(subject.split()).strip("[] ")
    if not clean_subject or clean_subject in answer:
        return answer
    return f"{clean_subject}: {answer}"


def _ollama_chat_url(openai_base_url: str) -> str:
    base_url = openai_base_url.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url.removesuffix("/v1")
    return f"{base_url}/api/chat"


def _warmup_card() -> FeatureCard:
    return FeatureCard(
        feature_id="warmup",
        feature_name="제브라 패턴",
        category="manual_chunk",
        summary="제브라 패턴은 밝은 부분에 줄무늬를 표시합니다.",
        supported_models=[
            SupportedModel(model_id="DC-G9M2", support_status="unknown"),
        ],
        sources=[
            SourceReference(
                document_id="warmup",
                model_id="DC-G9M2",
                page=1,
                section_title="제브라 패턴",
                viewer_url="/api/viewer/warmup/pages/1",
            ),
        ],
        confidence=1.0,
    )
