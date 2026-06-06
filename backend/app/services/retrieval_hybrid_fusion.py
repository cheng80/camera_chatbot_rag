from dataclasses import dataclass

from backend.app.indexing.fts_index import FtsSearchResult
from backend.app.schemas.feature_card import FeatureCard
from backend.app.schemas.search import NormalizedQuery, SearchRequest, SearchResponse
from backend.app.services.retrieval_feature_cards import (
    response_from_fts_results,
    response_from_vector_results,
)
from backend.app.services.retrieval_source_validation import SourceValidationContext
from backend.app.services.vector_search import VectorSearchResult

type SourcePageKey = tuple[str, str, int]
RRF_K = 60


@dataclass(frozen=True, slots=True)
class RankedFeatureCard:
    card: FeatureCard
    score: float
    source_key: SourcePageKey


@dataclass(frozen=True, slots=True)
class HybridFusionInput:
    payload: SearchRequest
    normalized_query: NormalizedQuery
    fts_results: tuple[FtsSearchResult, ...]
    vector_results: tuple[VectorSearchResult, ...]
    requested_model_ids: tuple[str, ...]
    validation_context: SourceValidationContext
    index_exists: bool


def response_from_hybrid_results(
    *,
    fusion_input: HybridFusionInput,
) -> SearchResponse:
    fts_response = (
        response_from_fts_results(
            payload=fusion_input.payload,
            normalized_query=fusion_input.normalized_query,
            results=fusion_input.fts_results,
            requested_model_ids=fusion_input.requested_model_ids,
            validation_context=fusion_input.validation_context,
        )
        if fusion_input.fts_results
        else None
    )
    vector_response = response_from_vector_results(
        payload=fusion_input.payload,
        normalized_query=fusion_input.normalized_query,
        results=fusion_input.vector_results,
        requested_model_ids=fusion_input.requested_model_ids,
        validation_context=fusion_input.validation_context,
    )
    cards = _merge_cards(
        fts_cards=tuple(fts_response.cards) if fts_response is not None else (),
        vector_cards=tuple(vector_response.cards),
        top_k=fusion_input.payload.top_k,
    )
    if cards:
        return SearchResponse(
            query=fusion_input.payload.query,
            normalized_query=fusion_input.normalized_query,
            cards=list(cards),
            retrieval_status="ok",
        )
    if _has_unvalidated_candidates(
        fts_response=fts_response,
        vector_response=vector_response,
    ):
        return SearchResponse(
            query=fusion_input.payload.query,
            normalized_query=fusion_input.normalized_query,
            cards=[],
            retrieval_status="insufficient_evidence",
        )
    status = (
        "not_indexed"
        if not fusion_input.index_exists and not fusion_input.vector_results
        else "no_results"
    )
    return SearchResponse(
        query=fusion_input.payload.query,
        normalized_query=fusion_input.normalized_query,
        cards=[],
        retrieval_status=status,
    )


def _merge_cards(
    *,
    fts_cards: tuple[FeatureCard, ...],
    vector_cards: tuple[FeatureCard, ...],
    top_k: int,
) -> tuple[FeatureCard, ...]:
    scored_cards = tuple(
        _ranked_card(card=card, rank=rank, source="fts")
        for rank, card in enumerate(fts_cards, start=1)
    ) + tuple(
        _ranked_card(card=card, rank=rank, source="vector")
        for rank, card in enumerate(vector_cards, start=1)
    )
    best_by_source: dict[SourcePageKey, RankedFeatureCard] = {}
    for ranked_card in scored_cards:
        existing = best_by_source.get(ranked_card.source_key)
        if existing is None or ranked_card.score > existing.score:
            best_by_source[ranked_card.source_key] = ranked_card
    ranked = sorted(best_by_source.values(), key=lambda item: item.score, reverse=True)
    return tuple(item.card for item in ranked)[:top_k]


def _ranked_card(
    *,
    card: FeatureCard,
    rank: int,
    source: str,
) -> RankedFeatureCard:
    source_ref = card.sources[0]
    source_boost = 0.02 if source == "fts" else 0
    score = (1 / (RRF_K + rank)) + source_boost
    return RankedFeatureCard(
        card=card,
        score=score,
        source_key=(source_ref.document_id, source_ref.model_id, source_ref.page),
    )


def _has_unvalidated_candidates(
    *,
    fts_response: SearchResponse | None,
    vector_response: SearchResponse,
) -> bool:
    responses = tuple(
        response for response in (fts_response, vector_response) if response is not None
    )
    return any(
        response.retrieval_status == "insufficient_evidence"
        for response in responses
    )
