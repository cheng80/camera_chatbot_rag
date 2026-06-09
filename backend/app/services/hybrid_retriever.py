from dataclasses import dataclass
from pathlib import Path
from typing import Final

from backend.app.indexing.fts_index import (
    DEFAULT_FTS_INDEX_PATH,
    search_fts_index,
)
from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.schemas.feature_card import FeatureCard
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.feature_wiki_retriever import feature_wiki_cards_for_query
from backend.app.services.query_normalizer import (
    load_default_models,
    normalize_search_input,
)
from backend.app.services.retrieval_hybrid_fusion import (
    HybridFusionInput,
    response_from_hybrid_results,
)
from backend.app.services.retrieval_source_validation import (
    SourceValidationCache,
    SourceValidationContext,
)
from backend.app.services.vector_search import (
    VectorSearchAdapter,
    VectorSearchRequest,
)
from backend.app.wiki.source_ref_checker import (
    DEFAULT_PAGES_DIR,
    DEFAULT_REGISTRY_DIR,
)

SEARCH_CANDIDATE_TOP_K: Final = 1000
MIN_DEFAULT_FEATURE_WIKI_PROMOTION_TOKENS: Final = 2
NATURAL_LANGUAGE_FEATURE_TERMS: Final = frozenset(
    (
        "어디",
        "어디서",
        "어디에",
        "어떻게",
        "켜",
        "켜나요",
        "켜는",
        "설정",
        "켜?",
        "기능",
        "경고",
    ),
)


@dataclass(frozen=True, slots=True)
class HybridRetrieverConfig:
    index_path: Path = DEFAULT_FTS_INDEX_PATH
    registry_dir: Path = DEFAULT_REGISTRY_DIR
    pages_dir: Path = DEFAULT_PAGES_DIR
    models: tuple[CameraModelRegistryEntry, ...] | None = None
    model_aliases: tuple[tuple[str, str], ...] = ()
    vector_adapter: VectorSearchAdapter | None = None
    feature_wiki_path: Path | None = None


class HybridRetriever:
    def __init__(
        self,
        *,
        config: HybridRetrieverConfig | None = None,
    ) -> None:
        resolved_config = config or HybridRetrieverConfig()
        self._index_path: Path = resolved_config.index_path
        self._registry_dir: Path = resolved_config.registry_dir
        self._pages_dir: Path = resolved_config.pages_dir
        self._models: tuple[CameraModelRegistryEntry, ...] = (
            resolved_config.models
            if resolved_config.models is not None
            else load_default_models()
        )
        self._model_aliases: tuple[tuple[str, str], ...] = (
            resolved_config.model_aliases
        )
        self._vector_adapter: VectorSearchAdapter | None = (
            resolved_config.vector_adapter
        )
        self._feature_wiki_path: Path | None = resolved_config.feature_wiki_path
        self._source_validation_cache: SourceValidationCache = {}

    def search(self, payload: SearchRequest) -> SearchResponse:
        normalized_input = normalize_search_input(
            query=payload.query,
            requested_model_ids=payload.model_ids,
            models=self._models,
            extra_model_aliases=self._model_aliases,
        )
        results = search_fts_index(
            index_path=self._index_path,
            query=normalized_input.search_query,
            model_ids=normalized_input.effective_model_ids,
            top_k=candidate_search_top_k(payload.top_k),
        )
        vector_results = (
            self._vector_adapter.search(
                VectorSearchRequest(
                    query=normalized_input.search_query,
                    model_ids=tuple(normalized_input.effective_model_ids),
                    top_k=candidate_search_top_k(payload.top_k),
                ),
            )
            if self._vector_adapter is not None
            else ()
        )
        validation_context = SourceValidationContext(
            registry_dir=self._registry_dir,
            pages_dir=self._pages_dir,
            validation_cache=self._source_validation_cache,
        )
        response = response_from_hybrid_results(
            fusion_input=HybridFusionInput(
                payload=payload,
                normalized_query=normalized_input.normalized_query,
                fts_results=results,
                vector_results=vector_results,
                requested_model_ids=tuple(normalized_input.effective_model_ids),
                validation_context=validation_context,
                index_exists=self._index_path.is_file(),
            ),
        )
        wiki_cards = feature_wiki_cards_for_query(
            wiki_path=self._feature_wiki_path,
            query=normalized_input.search_query,
            requested_model_ids=tuple(normalized_input.effective_model_ids),
            validation_context=validation_context,
        )
        if not wiki_cards:
            return response
        if payload.include_feature_wiki_candidates:
            return response.model_copy(
                update={
                    "cards": [*response.cards, *wiki_cards],
                    "retrieval_status": "ok",
                },
            )
        if not _should_prepend_feature_wiki_candidates(
            query=normalized_input.search_query,
            wiki_cards=wiki_cards,
        ):
            return response
        return response.model_copy(
            update={
                "cards": _prepend_feature_wiki_cards(
                    response_cards=tuple(response.cards),
                    wiki_cards=wiki_cards,
                    top_k=payload.top_k,
                ),
                "retrieval_status": "ok",
            },
        )


def candidate_search_top_k(_final_top_k: int) -> int:
    return SEARCH_CANDIDATE_TOP_K


def _should_prepend_feature_wiki_candidates(
    *,
    query: str,
    wiki_cards: tuple[FeatureCard, ...],
) -> bool:
    query_tokens = tuple(query.casefold().split())
    if not query_tokens:
        return False
    if len(query_tokens) < MIN_DEFAULT_FEATURE_WIKI_PROMOTION_TOKENS:
        return False
    if _is_exact_feature_name_query(query=query, wiki_cards=wiki_cards):
        return False
    return any(
        term in token
        for token in query_tokens
        for term in NATURAL_LANGUAGE_FEATURE_TERMS
    )


def _is_exact_feature_name_query(
    *,
    query: str,
    wiki_cards: tuple[FeatureCard, ...],
) -> bool:
    normalized_query = query.casefold().strip()
    return any(
        normalized_query == card.feature_name.casefold().strip() for card in wiki_cards
    )


def _prepend_feature_wiki_cards(
    *,
    response_cards: tuple[FeatureCard, ...],
    wiki_cards: tuple[FeatureCard, ...],
    top_k: int,
) -> list[FeatureCard]:
    cards: list[FeatureCard] = []
    seen_feature_ids: set[str] = set()
    for card in (*wiki_cards, *response_cards):
        if card.feature_id in seen_feature_ids:
            continue
        seen_feature_ids.add(card.feature_id)
        cards.append(card)
        if len(cards) >= top_k:
            break
    return cards
