from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
    SupportedModel,
)
from backend.app.services.feature_wiki_scoring import (
    MIN_FEATURE_WIKI_SCORE,
    display_feature_name,
    is_instruction_like_label,
    score_feature_wiki_entry,
    scoring_tokens,
)
from backend.app.services.retrieval_source_validation import (
    SourceValidationContext,
    validate_source_reference_cached,
    viewer_url,
)
from backend.app.wiki.generator import (
    FeatureConfidence,
    FeatureSourceRef,
    FeatureWikiEntry,
    load_feature_wiki_json,
)
from backend.app.wiki.source_ref_checker import SourceReferenceCandidate

MAX_FEATURE_WIKI_CANDIDATES: Final = 8
CONFIDENCE_SCORES: Final[dict[FeatureConfidence, float]] = {
    "verified": 0.75,
    "weak": 0.6,
}


@dataclass(frozen=True, slots=True)
class RankedFeatureWikiCard:
    card: FeatureCard
    score: float


def feature_wiki_cards_for_query(
    *,
    wiki_path: Path | None,
    query: str,
    requested_model_ids: tuple[str, ...],
    validation_context: SourceValidationContext,
) -> tuple[FeatureCard, ...]:
    if wiki_path is None:
        return ()
    try:
        entries = load_feature_wiki_json(wiki_path)
    except FileNotFoundError:
        return ()
    except ValidationError:
        return ()
    query_tokens = scoring_tokens(query)
    ranked_cards = tuple(
        ranked_card
        for ranked_card in (
            _card_from_entry(
                entry=entry,
                query_tokens=query_tokens,
                requested_model_ids=requested_model_ids,
                validation_context=validation_context,
            )
            for entry in entries
        )
        if ranked_card is not None
    )
    return tuple(
        ranked_card.card
        for ranked_card in sorted(
            ranked_cards,
            key=lambda ranked_card: ranked_card.score,
            reverse=True,
        )
    )[:MAX_FEATURE_WIKI_CANDIDATES]


def _card_from_entry(
    *,
    entry: FeatureWikiEntry,
    query_tokens: tuple[str, ...],
    requested_model_ids: tuple[str, ...],
    validation_context: SourceValidationContext,
) -> RankedFeatureWikiCard | None:
    if is_instruction_like_label(entry.canonical_name):
        return None
    score = score_feature_wiki_entry(entry=entry, query_tokens=query_tokens)
    if score < MIN_FEATURE_WIKI_SCORE:
        return None
    source_refs = tuple(
        source_ref
        for source_ref in entry.source_refs
        if _matches_model_filter(
            source_model_ids=source_ref.model_ids,
            requested_model_ids=requested_model_ids,
        )
    )
    sources = tuple(
        source
        for source in (
            _source_reference(
                source_ref=source_ref,
                requested_model_ids=requested_model_ids,
                validation_context=validation_context,
            )
            for source_ref in source_refs
        )
        if source is not None
    )
    if not sources:
        return None
    return RankedFeatureWikiCard(
        card=FeatureCard(
            feature_id=f"feature_wiki:{entry.feature_id}",
            feature_name=display_feature_name(entry.canonical_name),
            category=entry.category,
            summary=source_refs[0].evidence,
            supported_models=[
                SupportedModel(model_id=model_id, support_status="supported")
                for model_id in _supported_model_ids(source_refs)
            ],
            sources=list(sources),
            evidence_status="source_validated",
            confidence=_confidence_score(entry.confidence),
        ),
        score=score,
    )


def _source_reference(
    *,
    source_ref: FeatureSourceRef,
    requested_model_ids: tuple[str, ...],
    validation_context: SourceValidationContext,
) -> SourceReference | None:
    model_id = _source_model_id(
        source_model_ids=source_ref.model_ids,
        requested_model_ids=requested_model_ids,
    )
    validation_result = validate_source_reference_cached(
        reference=SourceReferenceCandidate(
            document_id=source_ref.document_id,
            model_id=model_id,
            page=source_ref.page,
        ),
        validation_context=validation_context,
    )
    if not validation_result.valid:
        return None
    return SourceReference(
        document_id=source_ref.document_id,
        model_id=model_id,
        page=source_ref.page,
        section_title=source_ref.section_id,
        viewer_url=viewer_url(
            document_id=source_ref.document_id,
            page=source_ref.page,
            validation_result=validation_result,
        ),
    )



def _matches_model_filter(
    *,
    source_model_ids: tuple[str, ...],
    requested_model_ids: tuple[str, ...],
) -> bool:
    return not requested_model_ids or bool(
        set(source_model_ids).intersection(requested_model_ids),
    )


def _source_model_id(
    *,
    source_model_ids: tuple[str, ...],
    requested_model_ids: tuple[str, ...],
) -> str:
    for model_id in requested_model_ids:
        if model_id in source_model_ids:
            return model_id
    return source_model_ids[0]


def _supported_model_ids(source_refs: tuple[FeatureSourceRef, ...]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            model_id
            for source_ref in source_refs
            for model_id in source_ref.model_ids
        ),
    )


def _confidence_score(confidence: FeatureConfidence) -> float:
    return CONFIDENCE_SCORES[confidence]
