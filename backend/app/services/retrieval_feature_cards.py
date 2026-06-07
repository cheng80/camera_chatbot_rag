from dataclasses import dataclass
from typing import Final

from backend.app.indexing.fts_index import FtsSearchResult
from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
    SupportedModel,
)
from backend.app.schemas.search import NormalizedQuery, SearchRequest, SearchResponse
from backend.app.services.retrieval_reference_pages import referenced_page_for_query
from backend.app.services.retrieval_source_validation import (
    SourceValidationContext,
    validate_source_reference_cached,
    viewer_url,
)
from backend.app.services.vector_search import VectorSearchResult
from backend.app.wiki.source_ref_checker import (
    SourceReferenceCandidate,
    SourceReferenceValidationResult,
)

DEFAULT_CATEGORY: Final = "manual_chunk"
SUMMARY_LIMIT: Final = 180
type SourcePageKey = tuple[str, str, int]


@dataclass(frozen=True, slots=True)
class FeatureCardData:
    feature_id: str
    feature_name: str
    content: str
    model_ids: tuple[str, ...]
    source: SourceReference
    validation_result: SourceReferenceValidationResult
    confidence: float


def response_from_fts_results(
    *,
    payload: SearchRequest,
    normalized_query: NormalizedQuery,
    results: tuple[FtsSearchResult, ...],
    requested_model_ids: tuple[str, ...],
    validation_context: SourceValidationContext,
) -> SearchResponse:
    cards = tuple(
        card
        for card in (
            _card_from_result(
                result=result,
                normalized_query=normalized_query,
                requested_model_ids=requested_model_ids,
                validation_context=validation_context,
            )
            for result in deduplicate_source_pages(
                results=results,
                requested_model_ids=requested_model_ids,
            )
        )
        if card.evidence_status == "source_validated"
    )
    if not cards:
        return SearchResponse(
            query=payload.query,
            normalized_query=normalized_query,
            cards=[],
            retrieval_status="insufficient_evidence",
        )
    return SearchResponse(
        query=payload.query,
        normalized_query=normalized_query,
        cards=list(cards),
        retrieval_status="ok",
    )


def response_from_vector_results(
    *,
    payload: SearchRequest,
    normalized_query: NormalizedQuery,
    results: tuple[VectorSearchResult, ...],
    requested_model_ids: tuple[str, ...],
    validation_context: SourceValidationContext,
) -> SearchResponse:
    cards = tuple(
        card
        for card in (
            _card_from_vector_result(
                result=result,
                requested_model_ids=requested_model_ids,
                validation_context=validation_context,
            )
            for result in results
        )
        if card.evidence_status == "source_validated"
    )
    if not cards:
        status = "insufficient_evidence" if results else "no_results"
        return SearchResponse(
            query=payload.query,
            normalized_query=normalized_query,
            cards=[],
            retrieval_status=status,
        )
    return SearchResponse(
        query=payload.query,
        normalized_query=normalized_query,
        cards=list(cards),
        retrieval_status="ok",
    )


def deduplicate_source_pages(
    *,
    results: tuple[FtsSearchResult, ...],
    requested_model_ids: tuple[str, ...],
) -> tuple[FtsSearchResult, ...]:
    seen_source_pages: set[SourcePageKey] = set()
    deduplicated: list[FtsSearchResult] = []
    for result in results:
        selected_model_id = source_model_id(
            result_model_ids=result.model_ids,
            requested_model_ids=requested_model_ids,
        )
        source_key = (result.document_id, selected_model_id, result.page_start)
        if source_key in seen_source_pages:
            continue
        seen_source_pages.add(source_key)
        deduplicated.append(result)
    return tuple(deduplicated)


def source_model_id(
    *,
    result_model_ids: tuple[str, ...],
    requested_model_ids: tuple[str, ...],
) -> str:
    for model_id in requested_model_ids:
        if model_id in result_model_ids:
            return model_id
    return result_model_ids[0]


def _card_from_vector_result(
    *,
    result: VectorSearchResult,
    requested_model_ids: tuple[str, ...],
    validation_context: SourceValidationContext,
) -> FeatureCard:
    feature_name = result.section_title or "vector_match"
    source_id = source_model_id(
        result_model_ids=result.model_ids,
        requested_model_ids=requested_model_ids,
    )
    validation_result = validate_source_reference_cached(
        reference=SourceReferenceCandidate(
            document_id=result.document_id,
            model_id=source_id,
            page=result.page_start,
        ),
        validation_context=validation_context,
    )
    return _feature_card(
        FeatureCardData(
            feature_id=result.chunk_id,
            feature_name=feature_name,
            content=result.content,
            model_ids=result.model_ids,
            source=SourceReference(
                document_id=result.document_id,
                model_id=source_id,
                page=result.page_start,
                section_title=feature_name,
                viewer_url=viewer_url(
                    document_id=result.document_id,
                    page=result.page_start,
                    validation_result=validation_result,
                ),
            ),
            validation_result=validation_result,
            confidence=result.score,
        ),
    )


def _card_from_result(
    *,
    result: FtsSearchResult,
    normalized_query: NormalizedQuery,
    requested_model_ids: tuple[str, ...],
    validation_context: SourceValidationContext,
) -> FeatureCard:
    feature_name = result.section_title or result.chunk_type
    source_id = source_model_id(
        result_model_ids=result.model_ids,
        requested_model_ids=requested_model_ids,
    )
    referenced_page = referenced_page_for_query(
        result=result,
        normalized_query=normalized_query,
    )
    source_page = (
        referenced_page.page if referenced_page is not None else result.page_start
    )
    source_title = (
        referenced_page.label if referenced_page is not None else feature_name
    )
    validation_result = validate_source_reference_cached(
        reference=SourceReferenceCandidate(
            document_id=result.document_id,
            model_id=source_id,
            page=source_page,
        ),
        validation_context=validation_context,
    )
    return _feature_card(
        FeatureCardData(
            feature_id=result.chunk_id,
            feature_name=feature_name,
            content=result.content,
            model_ids=result.model_ids,
            source=SourceReference(
                document_id=result.document_id,
                model_id=source_id,
                page=source_page,
                section_title=source_title,
                viewer_url=viewer_url(
                    document_id=result.document_id,
                    page=source_page,
                    validation_result=validation_result,
                ),
            ),
            validation_result=validation_result,
            confidence=0.55,
        ),
    )


def _feature_card(data: FeatureCardData) -> FeatureCard:
    evidence_status = (
        "source_validated" if data.validation_result.valid else "insufficient_evidence"
    )
    return FeatureCard(
        feature_id=data.feature_id,
        feature_name=data.feature_name,
        category=DEFAULT_CATEGORY,
        summary=_summary(data.content),
        supported_models=[
            SupportedModel(model_id=model_id, support_status="unknown")
            for model_id in data.model_ids
        ],
        how_to_use=[],
        menu_path=None,
        cautions=[],
        sources=[data.source],
        evidence_status=evidence_status,
        source_validation_errors=[
            error.code for error in data.validation_result.errors
        ],
        confidence=data.confidence,
    )


def _summary(content: str) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= SUMMARY_LIMIT:
        return normalized
    return f"{normalized[:SUMMARY_LIMIT]}..."
