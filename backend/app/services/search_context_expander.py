from collections.abc import Callable
from dataclasses import dataclass, field
from types import TracebackType
from typing import ClassVar, Protocol, Self

import httpx2
from pydantic import BaseModel, ConfigDict

from backend.app.core.settings import Settings
from backend.app.schemas.feature_card import FeatureCard
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.schemas.search_expand import SearchExpandResponse

EXPANSION_NOTICE = (
    "LLM으로 한국어 질문 의도를 해석해 관련 검색어를 확장했습니다. "
    "이 경로는 기본 검색보다 더 오래 걸릴 수 있습니다."
)
UNAVAILABLE_NOTICE = (
    "LLM 문맥 확장을 사용할 수 없어 기본 검색 결과를 유지했습니다."
)
MAX_EXPANDED_QUERY_LENGTH = 80
EXPANDED_SEARCH_TOP_K = 80
ADDED_CARD_LIMIT = 24
MIN_TOKEN_LENGTH = 2
MIN_EXPANDED_TOKEN_OVERLAP = 2
RELEVANCE_STOPWORDS = frozenset(
    {
        "관련",
        "검색",
        "방법",
        "변경",
        "메뉴",
        "카메라",
        "정보",
        "리셋",
    },
)
type SearchRunner = Callable[[SearchRequest], SearchResponse]
type SourceKey = tuple[str, str, int]


class SearchExpansionClient(Protocol):
    def expand(
        self,
        *,
        model_id: str,
        query: str,
        max_terms: int,
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
class OllamaSearchExpansionClient:
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

    def expand(
        self,
        *,
        model_id: str,
        query: str,
        max_terms: int,
        max_tokens: int,
        think: bool,
    ) -> str:
        response = self._client.post(
            _ollama_chat_url(self.settings.llm_base_url),
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
            json={
                "model": model_id,
                "messages": _expansion_messages(query=query, max_terms=max_terms),
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


def expand_search_response(
    *,
    payload: SearchRequest,
    settings: Settings,
    search_runner: SearchRunner,
    client: SearchExpansionClient | None = None,
) -> SearchExpandResponse:
    base_response = search_runner(payload)
    if not settings.llm_query_expansion_enabled:
        return _unavailable_response(response=base_response)
    if client is None:
        with OllamaSearchExpansionClient(settings=settings) as expansion_client:
            return _expand_with_client(
                payload=payload,
                settings=settings,
                search_runner=search_runner,
                base_response=base_response,
                client=expansion_client,
            )
    return _expand_with_client(
        payload=payload,
        settings=settings,
        search_runner=search_runner,
        base_response=base_response,
        client=client,
    )


def _expand_with_client(
    *,
    payload: SearchRequest,
    settings: Settings,
    search_runner: SearchRunner,
    base_response: SearchResponse,
    client: SearchExpansionClient,
) -> SearchExpandResponse:
    expanded_queries = _expanded_queries(
        query=payload.query,
        settings=settings,
        client=client,
        max_terms=_max_terms(payload=payload, settings=settings),
    )
    if not expanded_queries:
        return _unavailable_response(response=base_response)
    response = _merged_search_response(
        payload=payload,
        search_runner=search_runner,
        base_response=base_response,
        expanded_queries=expanded_queries,
    )
    return SearchExpandResponse(
        status="ok",
        notice=EXPANSION_NOTICE,
        expanded_queries=list(expanded_queries),
        response=response,
    )


def _expanded_queries(
    *,
    query: str,
    settings: Settings,
    client: SearchExpansionClient,
    max_terms: int,
) -> tuple[str, ...]:
    for model_id in _expansion_model_ids(settings):
        try:
            content = client.expand(
                model_id=model_id,
                query=query,
                max_terms=max_terms,
                max_tokens=settings.llm_query_expansion_max_tokens,
                think=settings.llm_query_expansion_think,
            )
        except httpx2.HTTPError:
            continue
        parsed = _parse_expanded_queries(content=content, original_query=query)
        if parsed:
            return parsed[:max_terms]
    return ()


def _merged_search_response(
    *,
    payload: SearchRequest,
    search_runner: SearchRunner,
    base_response: SearchResponse,
    expanded_queries: tuple[str, ...],
) -> SearchResponse:
    base_cards = list(base_response.cards)
    base_source_keys = _source_keys(base_cards)
    added_cards: list[FeatureCard] = []
    for query in expanded_queries:
        response = search_runner(
            payload.model_copy(
                update={
                    "query": query,
                    "top_k": min(payload.top_k, EXPANDED_SEARCH_TOP_K),
                },
            ),
        )
        added_cards.extend(
            card
            for card in response.cards
            if _source_key(card) not in base_source_keys
            and _is_relevant_added_card(
                card=card,
                original_query=payload.query,
                expanded_query=query,
            )
        )
    merged_cards = _deduplicate_cards(
        [*added_cards[:ADDED_CARD_LIMIT], *base_cards],
    )
    status = "ok" if merged_cards else base_response.retrieval_status
    return base_response.model_copy(
        update={
            "cards": list(merged_cards),
            "retrieval_status": status,
        },
    )


def _parse_expanded_queries(*, content: str, original_query: str) -> tuple[str, ...]:
    seen: set[str] = {original_query.strip()}
    parsed: list[str] = []
    for line in content.splitlines():
        cleaned = _clean_query_line(line)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        parsed.append(cleaned)
    return tuple(parsed)


def _clean_query_line(value: str) -> str:
    cleaned = value.strip()
    cleaned = cleaned.lstrip("-*•0123456789.、) ")
    cleaned = cleaned.strip("\"'`[] ")
    if not cleaned or len(cleaned) > MAX_EXPANDED_QUERY_LENGTH:
        return ""
    if any(token in cleaned for token in ("{", "}", "```", ":")):
        return ""
    return " ".join(cleaned.split())


def _deduplicate_cards(cards: list[FeatureCard]) -> tuple[FeatureCard, ...]:
    seen: set[SourceKey] = set()
    deduplicated: list[FeatureCard] = []
    for card in cards:
        key = _source_key(card)
        if key is None:
            continue
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(card)
    return tuple(deduplicated)


def _source_keys(cards: list[FeatureCard]) -> set[SourceKey]:
    return {key for card in cards if (key := _source_key(card)) is not None}


def _source_key(card: FeatureCard) -> SourceKey | None:
    source = card.sources[0] if card.sources else None
    if source is None:
        return None
    return (source.document_id, source.model_id, source.page)


def _is_relevant_added_card(
    *,
    card: FeatureCard,
    original_query: str,
    expanded_query: str,
) -> bool:
    card_text = _card_text(card)
    original_tokens = _meaningful_tokens(original_query)
    expanded_tokens = _meaningful_tokens(expanded_query)
    if not expanded_tokens:
        return False
    expanded_overlap = expanded_tokens & card_text
    if not expanded_overlap:
        return False
    if len(expanded_overlap) >= MIN_EXPANDED_TOKEN_OVERLAP:
        return True
    return len(original_tokens & card_text) >= MIN_EXPANDED_TOKEN_OVERLAP


def _card_text(card: FeatureCard) -> set[str]:
    values = [card.feature_name, card.summary]
    values.extend(source.section_title for source in card.sources)
    return _meaningful_tokens(" ".join(values))


def _meaningful_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for raw_token in value.replace("+", " ").replace("/", " ").split():
        token = raw_token.strip(".,:;!?()[]{}\"'`")
        if len(token) < MIN_TOKEN_LENGTH or token in RELEVANCE_STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def _unavailable_response(*, response: SearchResponse) -> SearchExpandResponse:
    return SearchExpandResponse(
        status="unavailable",
        notice=UNAVAILABLE_NOTICE,
        expanded_queries=[],
        response=response,
    )


def _expansion_model_ids(settings: Settings) -> tuple[str, ...]:
    return (
        settings.llm_query_expansion_model,
        *settings.llm_query_expansion_fallback_models,
    )


def _max_terms(*, payload: SearchRequest, settings: Settings) -> int:
    configured = settings.llm_query_expansion_max_terms
    requested = getattr(payload, "max_expanded_queries", configured)
    return min(configured, int(requested))


def _expansion_messages(
    *,
    query: str,
    max_terms: int,
) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": (
                "You expand Korean camera manual search queries. "
                "Return only short Korean search queries, one per line. "
                "Keep the original query's main subject. "
                "Do not introduce unrelated features, menus, dates, time settings, "
                "or maintenance topics unless the original query mentions them. "
                "Avoid generic queries ending only in information, guide, or menu. "
                "Do not answer the user. Do not add facts. Do not output JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Original query:\n{query}\n\n"
                f"Return up to {max_terms} related manual-search queries. "
                "Prefer feature names, symptom terms, menu labels, and common Korean "
                "synonyms likely to appear in official camera manuals. "
                "Every returned line must be directly useful for finding the same "
                "manual topic as the original query."
            ),
        },
    )


def _ollama_chat_url(openai_base_url: str) -> str:
    base_url = openai_base_url.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url.removesuffix("/v1")
    return f"{base_url}/api/chat"
